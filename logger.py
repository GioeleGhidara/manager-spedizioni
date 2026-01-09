import os
import time
import functools
from datetime import datetime

# --- BLURRER ---

SENSITIVE_KEYS = {
    "token", "apikey", "api_key",
    "address", "phone", "name",
    "postalcode", "city",
    "tracking", "order_id"
}

def safe_repr(obj):
    """
    Rappresentazione sicura per i log.
    Oscura automaticamente i campi sensibili.
    """
    try:
        if isinstance(obj, dict):
            return {
                k: ("***" if k.lower() in SENSITIVE_KEYS else safe_repr(v))
                for k, v in obj.items()
            }
        elif isinstance(obj, (list, tuple)):
            return [safe_repr(x) for x in obj]
        elif isinstance(obj, str):
            if len(obj) > 60:
                return obj[:20] + "..." + obj[-10:]
            return obj
        return obj
    except Exception:
        return "***"

# --- CONFIGURAZIONE ---
K = 30                  # I log piu vecchi di questi giorni verranno cancellati
CARTELLA_LOG = "logs"   # Nome della cartella

class GestoreLog:
    def __init__(self, cartella_output=CARTELLA_LOG, giorni_conservazione=K):
        self.cartella = cartella_output
        self.giorni_conservazione = giorni_conservazione

        # 1. Crea la cartella se non esiste
        if not os.path.exists(self.cartella):
            try:
                os.makedirs(self.cartella)
                print(f"[Sistema] Cartella '{self.cartella}' creata.")
            except OSError as e:
                print(f"[Sistema] Errore creazione cartella log: {e}")

        # 2. Esegue la pulizia automatica all'avvio
        self._pulizia_automatica()

    def _pulizia_automatica(self):
        # Elimina i file .txt piu vecchi di K giorni
        try:
            adesso = time.time()
            limite_tempo = adesso - (self.giorni_conservazione * 86400)  # 86400 sec = 1 giorno
            count = 0

            if os.path.exists(self.cartella):
                for nome_file in os.listdir(self.cartella):
                    percorso = os.path.join(self.cartella, nome_file)
                    # Controlla che sia un file .txt
                    if os.path.isfile(percorso) and nome_file.endswith(".txt"):
                        if os.path.getmtime(percorso) < limite_tempo:
                            os.remove(percorso)
                            count += 1
            if count > 0:
                print(f"[Sistema] Pulizia completata: rimossi {count} file vecchi.")
        except Exception as e:
            print(f"[Sistema] Errore pulizia log: {e}")

    def _scrivi(self, livello, icona, messaggio):
        # Scrive fisicamente nel file giornaliero.
        adesso = datetime.now()
        # Nome file rotativo: log_YYYY-mm-dd.txt
        nome_file = f"log_{adesso.strftime('%Y-%m-%d')}.txt"
        percorso = os.path.join(self.cartella, nome_file)

        # Formato: [ORA] | ICONA LIVELLO | MESSAGGIO
        riga = f"[{adesso.strftime('%H:%M:%S')}] | {icona} {livello:<7} | {messaggio}\n"

        try:
            with open(percorso, "a", encoding="utf-8") as f:
                f.write(riga)
            # print(riga.strip())  # Togliere # per visualizzare a schermo i log
        except Exception as e:
            print(f"!!! Errore scrittura log: {e}")

    # --- Metodi rapidi ---
    def info(self, msg):
        self._scrivi("INFO", "[INFO] ", msg)

    def successo(self, msg):
        self._scrivi("OK", "[OK] ", msg)

    def errore(self, msg):
        self._scrivi("ERROR", "[ERROR] ", msg)

    def warning(self, msg):
        self._scrivi("WARN", "[WARN] ", msg)

    def debug(self, msg):
        self._scrivi("DEBUG", "[DEBUG] ", msg)

# --- INIZIALIZZAZIONE ---
log = GestoreLog()

# --- IL DECORATORE PER TRACCIARE LE FUNZIONI ---
def traccia(func):
    """
    Versione 2.0: Logga Input, Output (riassunto) ed Errori.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        nome_func = func.__name__
        # Log Input
        log.debug(f"START: {nome_func} | Input: {safe_repr(args)} {safe_repr(kwargs)}")

        try:
            risultato = func(*args, **kwargs)

            # Log Output (intelligente)
            out_log = str(risultato)
            # Se e troppo lungo (es. file binario o lista enorme), lo tagliamo
            if len(out_log) > 100:
                if isinstance(risultato, list):
                    out_log = f"Lista di {len(risultato)} elementi"
                elif isinstance(risultato, dict):
                    out_log = f"Dizionario con {len(risultato)} chiavi"
                else:
                    out_log = out_log[:100] + "..."

            log.debug(f"END: {nome_func} | Output: {out_log}")
            return risultato

        except Exception as e:
            log.errore(f"CRASH: {nome_func} fallita. Motivo: {e}")
            raise
    return wrapper

if __name__ == "__main__":
    # 1. Esempio: Una funzione normale che fa una richiesta (simulata)
    @traccia
    def scarica_ordini_ebay(stato_ordine):
        log.info("Contattando il server eBay...")
        time.sleep(1)  # Simula attesa
        return ["Ordine #123", "Ordine #456"]

    # 2. Esempio: Una funzione che accetta dati e calcola qualcosa
    @traccia
    def calcola_costo_spedizione(peso, corriere="DHL"):
        if peso > 100:
            raise ValueError("Pacco troppo pesante per questo corriere!")
        return peso * 5.50

    # --- ESECUZIONE REALE ---
    log.successo("Programma avviato correttamente.")

    try:
        # Chiamata tracciata con successo
        ordini = scarica_ordini_ebay("DA_SPEDIRE")
        log.info(f"Ho trovato {len(ordini)} ordini.")

        # Chiamata tracciata che andra in ERRORE (simulato)
        costo = calcola_costo_spedizione(150, corriere="Poste")

    except Exception:
        log.warning("Il programma ha gestito un errore ed e andato avanti.")

    log.successo("Programma terminato.")
