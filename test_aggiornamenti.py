import sys
import os

# 1. TEST IMPORTAZIONI CONFIG
print("🔹 1. Test Configurazione...")
try:
    from config import EBAY_XML_API_URL, EBAY_NS
    print(f"   ✅ Costanti lette da config: {EBAY_XML_API_URL}")
except ImportError as e:
    print(f"   ❌ ERRORE: Non trovo le costanti in config.py! ({e})")
    sys.exit()

# 2. TEST CHECK TOKEN (con le nuove costanti)
print("\n🔹 2. Test Modulo Token...")
try:
    from check_token import check_scadenza_token_silenzioso
    # Eseguiamo la funzione. Se torna None o una stringa, vuol dire che non è crashata.
    risultato = check_scadenza_token_silenzioso()
    if risultato is None:
        print("   ✅ Check Token eseguito: Nessun avviso (Tutto OK).")
    else:
        print(f"   ⚠️  Check Token eseguito: {risultato}")
except Exception as e:
    print(f"   ❌ ERRORE in check_token.py: {e}")

# 3. TEST SHIPITALIA (LISTA SPEDIZIONI)
print("\n🔹 3. Test ShipItalia (Lista Semplificata)...")
try:
    from shipitalia import get_lista_spedizioni
    lista = get_lista_spedizioni(limit=3)
    
    if isinstance(lista, list):
        print(f"   ✅ API ShipItalia OK: Scaricati {len(lista)} elementi.")
        if len(lista) > 0:
            print(f"      Esempio: {lista[0].get('trackingCode', 'N.D.')}")
    else:
        print(f"   ❌ ERRORE: La funzione non ha restituito una lista, ma: {type(lista)}")
        print(f"      Contenuto: {lista}")
except Exception as e:
    print(f"   ❌ CRASH ShipItalia: {e}")

# 4. TEST SHIPITALIA (SANITIZZAZIONE PAYLOAD)
print("\n🔹 4. Test Logica Troncamento (Senza _trunca)...")
try:
    from shipitalia import _prepara_payload_sicuro
    
    # Simuliamo un payload con dati TROPPO LUNGHI e spazi extra
    payload_test = {
        "sender": {
            "name": "   Mario Rossi con un nome lunghissimo che supera i 40 caratteri sicuramente   ",
            "city": "Città Molto Lunga E Distante"
        },
        "recipient": {
            "name": "Luigi",
            "address": "Via Corta"
        }
    }
    
    clean = _prepara_payload_sicuro(payload_test)
    nome_pulito = clean['sender']['name']
    
    print(f"   INPUT: '{payload_test['sender']['name']}' ({len(payload_test['sender']['name'])} chars)")
    print(f"   OUTPUT: '{nome_pulito}' ({len(nome_pulito)} chars)")
    
    if len(nome_pulito) <= 40 and "sicuramente" not in nome_pulito:
        print("   ✅ Il troncamento funziona correttamente!")
    else:
        print("   ❌ ERRORE: Il testo non è stato troncato bene.")

except ImportError:
    print("   ⚠️  Impossibile testare _prepara_payload_sicuro (forse è privata/non importabile), ma il resto è OK.")
except Exception as e:
    print(f"   ❌ ERRORE logica payload: {e}")

print("\n--- TEST COMPLETATI ---")