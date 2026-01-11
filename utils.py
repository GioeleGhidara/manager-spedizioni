from datetime import datetime

import config
import math
import re
import requests

import logger
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_TRACKING_CACHE = {}


def get_robust_session():
    """
    Crea una requests.Session con retry/backoff robusti.

    Note:
    - include retry anche su POST (utile per API esterne che possono rispondere 5xx/429)
    - rispetta Retry-After quando presente
    """
    session = requests.Session()
    retry_kwargs = dict(
        total=config.HTTP_RETRIES,
        read=config.HTTP_RETRIES,
        connect=config.HTTP_RETRIES,
        backoff_factor=config.HTTP_BACKOFF_FACTOR,
        status_forcelist=[408, 429, 500, 502, 503, 504],
        respect_retry_after_header=True,
    )

    allowed = frozenset({"HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"})
    try:
        retry = Retry(**retry_kwargs, allowed_methods=allowed)
    except TypeError:
        # Compatibilità con urllib3 < 2 (parametro rinominato)
        retry = Retry(**retry_kwargs, method_whitelist=allowed)

    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def arrotonda_peso_per_eccesso(peso: float) -> float:
    if peso <= 0:
        raise ValueError("Il peso deve essere positivo")
    return math.ceil(peso * 2) / 2

def normalizza_telefono(tel: str) -> str:
    """
    Formatta il telefono per ShipItalia (toglie prefisso intl).
    """
    tel = "".join(filter(str.isdigit, tel))
    if tel.startswith("0039"):
        tel = tel[4:]
    elif tel.startswith("39") and len(tel) > 10:
        tel = tel[2:]
    return tel

def valido_order_id(order_id: str) -> bool:
    """
    Verifica se l'Order ID ha un formato plausibile.
    Accetta sia il formato Legacy (12-12345-12345) 
    sia il formato REST API (v1|...|0).
    """
    # Se contiene pipe | è sicuramente un ID tecnico REST
    if "|" in order_id:
        return True
    
    # Altrimenti controlliamo il formato classico con i trattini
    return bool(re.match(r"^\d{2}-\d{5}-\d{5}$", order_id))

def genera_link_tracking(tracking_code: str) -> str:
    """Genera il link diretto per il tracking (attualmente Poste Italiane)."""
    return f"https://www.poste.it/cerca/#/risultati-spedizioni/{tracking_code}"

def get_stato_tracking_poste(tracking_code):
    """Scarica il JSON raw dalle API Poste."""
    if not tracking_code: return None
    
    url = 'https://www.poste.it/online/dovequando/DQ-REST/ricercasemplice'
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': 'https://www.poste.it',
        'Referer': 'https://www.poste.it/cerca/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
    }
    payload = {'tipoRichiedente': 'WEB', 'codiceSpedizione': tracking_code, 'periodoRicerca': 1}

    def _mask_tracking(code: str) -> str:
        if not code:
            return "N/A"
        if len(code) <= 6:
            return "***"
        return f"{code[:3]}...{code[-3:]}"

    try:
        session = get_robust_session()
        response = session.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.log.warning(
                f"Poste tracking HTTP {response.status_code} (tracking={_mask_tracking(tracking_code)})"
            )
            return None
        try:
            data = response.json()
        except ValueError as e:
            logger.log.warning(
                f"Poste tracking JSON non valido (tracking={_mask_tracking(tracking_code)}): {e}"
            )
            return None
        if not data:
            logger.log.warning(
                f"Poste tracking risposta vuota (tracking={_mask_tracking(tracking_code)})"
            )
        return data
    except requests.RequestException as e:
        logger.log.warning(
            f"Poste tracking richiesta fallita (tracking={_mask_tracking(tracking_code)}): {e}"
        )
    except Exception as e:
        logger.log.errore(
            f"Poste tracking errore inatteso (tracking={_mask_tracking(tracking_code)}): {e}"
        )
    return None

def get_stato_tracking_poste_cached(tracking_code, ttl_seconds=None):
    """
    Wrapper con cache in memoria per il tracking Poste.
    Usa TTL (secondi) per evitare chiamate ripetute.
    """
    if not tracking_code:
        return None
    if ttl_seconds is None:
        ttl_seconds = getattr(config, "TRACKING_CACHE_TTL_SECONDS", 3600)

    now = datetime.now()
    cached = _TRACKING_CACHE.get(tracking_code)
    if cached:
        age = (now - cached["ts"]).total_seconds()
        if age <= ttl_seconds:
            return cached["data"]

    data = get_stato_tracking_poste(tracking_code)
    if data is not None:
        _TRACKING_CACHE[tracking_code] = {"ts": now, "data": data}
        return data

    # Se la fetch fallisce e avevamo dati in cache, usiamo quelli stale.
    if cached:
        return cached["data"]
    return None



def estrai_stato_poste(dati_json):
    """Estrae lo stato piu recente da Poste, se presente."""
    if not dati_json:
        return ""
    if isinstance(dati_json, dict):
        movimenti = dati_json.get("listaMovimenti", [])
        if movimenti:
            ultimo = movimenti[-1]
            stato = ultimo.get("statoLavorazione") or ultimo.get("statoSpedizione")
            if stato:
                return str(stato)
        stato = dati_json.get("stato")
        if stato:
            return str(stato)
    if isinstance(dati_json, list) and dati_json:
        ultimo = dati_json[-1]
        if isinstance(ultimo, dict):
            stato = ultimo.get("statoLavorazione") or ultimo.get("statoSpedizione") or ultimo.get("stato")
            if stato:
                return str(stato)
    return ""
def formatta_stato_poste(dati_json):
    """
    Analizza il JSON di Poste e restituisce una stringa riassuntiva.
    Es: '10/01 14:30 | In consegna (Milano)'
    """
    if not dati_json: return "Nessuna info."
    
    movimenti = dati_json.get("listaMovimenti", [])
    if not movimenti:
        return f"Stato: {dati_json.get('stato', 'Sconosciuto')}"

    # L'ultimo elemento della lista è il più recente
    ultimo_evento = movimenti[-1]
    
    stato = ultimo_evento.get("statoLavorazione", "N.D.").strip()
    luogo = ultimo_evento.get("luogo", "").strip()
    
    # Conversione data da Millisecondi (Timestamp Unix * 1000)
    data_fmt = ""
    ts_ms = ultimo_evento.get("dataOra")
    if ts_ms:
        try:
            dt = datetime.fromtimestamp(ts_ms / 1000)
            data_fmt = dt.strftime("%d/%m %H:%M")
        except: pass

    # Costruiamo la stringa finale
    output = f"{stato}"
    if luogo: output += f" [{luogo}]"
    if data_fmt: output = f"{data_fmt} | {output}"
    
    return output

def estrai_messaggio_poste(dati_json):
    """Estrae un messaggio testuale da risposte Poste, se presente."""
    if isinstance(dati_json, dict):
        for key in ("messaggio", "message", "descrizione", "description", "msg", "errore", "error", "note"):
            val = dati_json.get(key)
            if isinstance(val, str) and val.strip():
                return val
        for key, val in dati_json.items():
            if isinstance(val, str) and "tracciatura" in val.lower():
                return val
    if isinstance(dati_json, list):
        for item in dati_json:
            if isinstance(item, dict):
                for key in ("messaggio", "message", "descrizione", "description", "msg", "errore", "error", "note"):
                    val = item.get(key)
                    if isinstance(val, str) and val.strip():
                        return val
    return ""

def estrai_posizione_poste(dati_json):
    """Estrae la posizione piu recente dalle risposte Poste, se presente."""
    if isinstance(dati_json, dict):
        movimenti = dati_json.get("listaMovimenti", [])
        if movimenti:
            ultimo = movimenti[-1]
            luogo = ultimo.get("luogo")
            if luogo:
                return str(luogo).title()
    if isinstance(dati_json, list) and dati_json:
        ultimo = dati_json[-1]
        if isinstance(ultimo, dict):
            luogo = ultimo.get("luogo") or ultimo.get("sede") or ultimo.get("city")
            if luogo:
                return str(luogo).title()
    return ""

