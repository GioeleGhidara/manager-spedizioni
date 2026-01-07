import os
import requests
import webbrowser
from config import API_URL_SHIPITALIA, SHIPITALIA_API_KEY
from logger import log, traccia # <--- IMPORT CORRETTO
from utils import get_robust_session
import copy

def _trunca(testo, lunghezza_max):
    if not testo: return ""
    return testo[:lunghezza_max].strip()

def _prepara_payload_sicuro(payload):
    """
    Rende il payload più "sicuro" per l'API, senza modificare l'oggetto originale.
    Troncamento campi per limiti ShipItalia.
    """
    p = copy.deepcopy(payload) if payload is not None else {}
    for role in ['sender', 'recipient']:
        if role in p and isinstance(p[role], dict):
            p[role]['name'] = _trunca(p[role].get('name', ''), 40)
            p[role]['address'] = _trunca(p[role].get('address', ''), 40)
            p[role]['city'] = _trunca(p[role].get('city', ''), 36)
    return p

def get_lista_spedizioni(limit=10):
    """
    Scarica la lista delle ultime spedizioni.
    Cerca automaticamente la lista reale dentro la risposta.
    """
    session = get_robust_session()
    url = f"https://shipitalia.com/api/shipments?page=1&limit={limit}"

    try:
        response = session.get(
            url,
            headers={
                "x-api-key": SHIPITALIA_API_KEY,
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        
        if response.status_code != 200:
            print(f"⚠️ Errore HTTP API: {response.status_code}")
            return []

        json_data = response.json()
        
        # 1. Verifica se c'è la chiave 'data'
        if isinstance(json_data, dict) and "data" in json_data:
            contenuto = json_data["data"]
            
            # CASO A: 'data' è direttamente la lista (perfetto)
            if isinstance(contenuto, list):
                return contenuto
            
            # CASO B: 'data' è un dizionario (contenitore) -> Cerchiamo la lista dentro
            if isinstance(contenuto, dict):
                # Cerca qualsiasi valore che sia una lista
                for chiave, valore in contenuto.items():
                    if isinstance(valore, list):
                        # Trovata! Restituiamo questa lista
                        # (es. contenuto['shipments'] o contenuto['items'])
                        return valore
                
                # Se arriviamo qui, è un dizionario ma senza liste dentro.
                # Stampiamo le chiavi per capire come si chiamano i campi
                print(f"⚠️ TROVATO DIZIONARIO MA NESSUNA LISTA. Chiavi disponibili: {list(contenuto.keys())}")
                return []

        # 2. Fallback: Se il JSON principale è una lista
        if isinstance(json_data, list):
            return json_data

        return []

    except Exception as e:
        log.errore(f"Errore recupero lista spedizioni: {e}")
        return []

@traccia
def verifica_stato_tracking(tracking_code):
    """
    Ottiene informazioni su una spedizione tramite codice di tracking.
    Documentazione: GET /api/tracking/:code

    Ritorno (sempre): dict con chiavi standard.
    """
    session = get_robust_session()
    url_tracking = f"https://shipitalia.com/api/tracking/{tracking_code}"

    result = {
        "ok": False,
        "trackingCode": tracking_code,
        "status": None,
        "status_code": None,
        "data": None,
        "error": None,
        "message": None,
    }

    try:
        log.info(f"Verifica stato tracking: {tracking_code}...")
        response = session.get(
            url_tracking,
            headers={
                "x-api-key": SHIPITALIA_API_KEY,
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        result["status_code"] = response.status_code

        if response.status_code == 404:
            result["error"] = "not_found"
            result["message"] = "Spedizione non trovata"
            return result
        if response.status_code == 401:
            result["error"] = "unauthorized"
            result["message"] = "API key non valida o non autorizzata"
            return result

        response.raise_for_status()

        dati = response.json() if response.content else None
        result["data"] = dati

        # Tentiamo di estrarre un dizionario "info" coerente se presente
        info = None
        if isinstance(dati, dict):
            info = dati.get("data") if "data" in dati else dati
        if isinstance(info, dict):
            result["status"] = info.get("status") or info.get("state")

        result["ok"] = True
        return result

    except requests.exceptions.RequestException as e:
        log.errore(f"Errore controllo tracking {tracking_code}: {e}")
        result["error"] = "request_error"
        result["message"] = str(e)
        # Se abbiamo una response, proviamo ad attaccare il body per debug
        try:
            if getattr(e, "response", None) is not None:
                result["status_code"] = e.response.status_code
                result["data"] = e.response.text
        except Exception:
            pass
        return result
    except Exception as e:
        log.errore(f"Errore controllo tracking {tracking_code}: {e}")
        result["error"] = "exception"
        result["message"] = str(e)
        return result

def scarica_pdf(url_pdf, tracking):
    session = get_robust_session()
    try:
        print(f"   ⬇️  Scaricamento etichetta in corso...")
        response = session.get(url_pdf, timeout=30)
        response.raise_for_status()
        
        os.makedirs("etichette", exist_ok=True)
        nome_file = os.path.join("etichette", f"{tracking}.pdf")
        
        with open(nome_file, "wb") as f:
            f.write(response.content)
            
        print(f"   💾 PDF Salvato: {nome_file}")
        log.info(f"PDF salvato in: {nome_file}")
        
        try:
            webbrowser.open(os.path.abspath(nome_file))
        except:
            pass 
            
        return nome_file
    except Exception as e:
        log.errore(f"Impossibile scaricare PDF da {url_pdf}: {e}")
        print(f"⚠️ Impossibile scaricare il PDF: {e}")
        return None

@traccia
def genera_etichetta(payload_originale):
    session = get_robust_session()
    
    # 1. Pulizia dati
    payload_clean = _prepara_payload_sicuro(payload_originale)
    
    try:
        # 2. Chiamata API
        response = session.post(
            API_URL_SHIPITALIA,
            json=payload_clean,
            headers={
                "x-api-key": SHIPITALIA_API_KEY,
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        
        dati_risposta = result.get("data", {})
        tracking = dati_risposta.get("trackingCode")
        pdf_url = dati_risposta.get("labelUrl")
        
        if not tracking:
            raise ValueError("L'API non ha restituito un Tracking Code!")

        # 4. Scaricamento Automatico PDF
        if pdf_url:
            scarica_pdf(pdf_url, tracking)
        
        return {
            "trackingCode": tracking,
            "labelUrl": pdf_url
        }

    except requests.exceptions.RequestException as e:
        log.errore(f"Errore API ShipItalia: {e}")
        # Logghiamo il payload che ha causato l'errore per debuggarlo
        log.debug(f"Payload fallito: {payload_clean}")
        
        if e.response is not None:
            print(f"🔍 Dettagli errore server: {e.response.text}")
            log.errore(f"Response Server: {e.response.text}")
            
        raise RuntimeError("Errore durante la generazione dell'etichetta") from e
    
