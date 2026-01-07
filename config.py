import os
from dotenv import load_dotenv

# Carica le variabili dal file .env (se presente)
load_dotenv()

# --- CONFIGURAZIONE RETE (RETRY) ---
HTTP_RETRIES = 3
HTTP_BACKOFF_FACTOR = 1  # 1s, 2s, 4s...

# --- VARIABILI D'AMBIENTE ---
SHIPITALIA_API_KEY = os.getenv("SHIPITALIA_API_KEY")
EBAY_XML_TOKEN = os.getenv("EBAY_XML_TOKEN") # <--- NUOVA VARIABILE

API_URL_SHIPITALIA = "https://shipitalia.com/api/generate-label"
MITTENTE_FILE = os.path.join("config", "mittente.txt")

def validate_config():
    """Controlla variabili necessarie."""
    required = {
        "SHIPITALIA_API_KEY": SHIPITALIA_API_KEY,
        "EBAY_XML_TOKEN": EBAY_XML_TOKEN,
    }
    missing = [key for key, val in required.items() if not val]
    if missing:
        raise RuntimeError(f"Variabili d'ambiente mancanti: {', '.join(missing)}")

