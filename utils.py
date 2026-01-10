import math
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import config

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
