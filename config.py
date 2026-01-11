import os
from dotenv import load_dotenv

# Carica il .env, ma NON sovrascrive se la variabile esiste già nel sistema
# (Così le Variabili d'Ambiente del PC vincono sul file .env)
load_dotenv(override=False)

# --- CONFIGURAZIONE RETE ---
HTTP_RETRIES = 3
HTTP_BACKOFF_FACTOR = 1
TRACKING_CACHE_TTL_SECONDS = 3600
TRACKING_MAX_WORKERS = 4

# --- VARIABILI D'AMBIENTE ---
# os.getenv leggerà indifferentemente dal Sistema o dal file .env
SHIPITALIA_API_KEY = os.getenv("SHIPITALIA_API_KEY")
EBAY_XML_TOKEN = os.getenv("EBAY_XML_TOKEN")

# Chiavi Sviluppatore eBay (Opzionali per l'uso base, necessarie per il check scadenza)
EBAY_APP_ID = os.getenv("EBAY_APP_ID")
EBAY_DEV_ID = os.getenv("EBAY_DEV_ID")
EBAY_CERT_ID = os.getenv("EBAY_CERT_ID")

# --- COSTANTI API ---
API_URL_SHIPITALIA = "https://shipitalia.com/api/generate-label"
MITTENTE_FILE = os.path.join("config", "mittente.txt")

EBAY_XML_API_URL = "https://api.ebay.com/ws/api.dll"
EBAY_NS = {'ns': 'urn:ebay:apis:eBLBaseComponents'}

def validate_config():
    """
    Controlla SOLO le variabili critiche per spedire.
    Le chiavi APP/DEV/CERT sono opzionali (servono solo al check token),
    quindi non blocchiamo il programma se mancano.
    """
    required = {
        "SHIPITALIA_API_KEY": SHIPITALIA_API_KEY,
        "EBAY_XML_TOKEN": EBAY_XML_TOKEN,
    }
    missing = [key for key, val in required.items() if not val]
    if missing:
        raise RuntimeError(
            f"Variabili d'ambiente mancanti: {', '.join(missing)}\n"
            "Verifica di averle inserite nel file .env o nelle Variabili di Sistema."
        )
