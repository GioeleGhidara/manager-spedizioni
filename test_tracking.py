import utils
import json

# Inserisci qui un codice tracking reale per provare (es. di una vecchia spedizione)
TRACKING_CODE = "1UW1RCW000396"  # Esempio dal tuo snippet

print(f"🔍 Cerco info per: {TRACKING_CODE}...")

dati = utils.get_stato_tracking_poste(TRACKING_CODE)

if dati:
    print("\n✅ RISPOSTA RAW (JSON):")
    print(json.dumps(dati, indent=4))
    
    # Esempio di come estrarre info utili se la struttura è standard
    # (La struttura varia in base allo stato, controlla il JSON output)
    if isinstance(dati, list) and len(dati) > 0:
        ultimo_stato = dati[0] # Spesso è una lista
        print(f"\n📦 Stato attuale: {ultimo_stato.get('statoSpedizione', 'N.D.')}")
        print(f"📅 Data: {ultimo_stato.get('dataOra', 'N.D.')}")
else:
    print("❌ Nessun dato trovato o errore nella richiesta.")