import sys
import os
import time

# Imposta encoding per evitare errori su Windows con icone
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from config import validate_config
from logger import log, traccia
from utils import valido_order_id
from input_utils import (
    chiedi_peso, 
    carica_mittente, 
    chiedi_destinatario, 
    chiedi_codice_sconto, 
    stampa_riepilogo, 
    conferma_operazione,
    gestisci_modifiche
)
from shipitalia import genera_etichetta, verifica_stato_tracking, get_lista_spedizioni, scarica_pdf
from ebay import gestisci_ordine_ebay, scarica_lista_ordini

def pulisci_schermo():
    """Pulisce la console per mantenere l'interfaccia ordinata."""
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    log.info("--- Avvio Applicazione ---")
    
    try:
        validate_config()
    except RuntimeError as e:
        msg = f"CONFIG ERROR: {e}"
        print(f"❌ {msg}")
        log.errore(msg)
        return

    # --- LOOP PRINCIPALE (Il programma non esce mai finché non premi 0) ---
    while True:
        pulisci_schermo()
        print("=== SPEDIZIONE MANAGER ===")
        print("\nCosa vuoi fare?")
        print("1) 📋 Dashboard Ordini (Da Spedire / In Viaggio)")
        print("2) ⌨️  Inserisci manualmente Order ID")
        print("3) 🚀 Etichetta rapida (No eBay)")
        print("4) 🔍 Storico Spedizioni & PDF")
        print("0) ❌ Esci")
        
        scelta_iniziale = input("\nScelta (0-4): ").strip()
        if scelta_iniziale: log.info(f"Utente nel menu principale: scelta {scelta_iniziale}")
        
        # Variabili di appoggio per il flusso
        order_id = ""
        destinatario_auto = None
        skip_standard_flow = False # Serve per saltare la creazione etichetta se usiamo menu 1 (solo visualizzazione) o 4

        # --- USCITA ---
        if scelta_iniziale == "0":
            print("👋 Alla prossima!")
            break

        # --- OPZIONE 1: DASHBOARD ---
        elif scelta_iniziale == "1":
            da_spedire, in_viaggio = scarica_lista_ordini(giorni_storico=30)

            if not da_spedire and not in_viaggio:
                print("\n✅ Nessun ordine attivo.")
                input("\nPremi INVIO per tornare al menu...")
                continue # Torna al menu principale

            print("\n" + "="*115)
            print(f" {'#':<3} | {'ID ORDINE':<16} | {'DATA':<11} | {'UTENTE':<15} | {'TITOLO OGGETTO'}")
            print("="*115)

            if da_spedire:
                print(" 🔴  DA SPEDIRE")
                for i, o in enumerate(da_spedire):
                    print(f" {i+1:<3} | {o['order_id'][:16]:<16} | {o['date']:<11} | {o['buyer']:<15} | {o['title']}")
            else:
                print(" ✅  Nessun ordine da spedire.")

            print("-" * 115)

            if in_viaggio:
                print(" 🚚  IN VIAGGIO")
                for o in in_viaggio:
                    print(f" {'•':<3} | {o['order_id'][:16]:<16} | {o['date']:<11} | {o['buyer']:<15} | {o['title']}")
            
            print("="*115)
            
            if not da_spedire:
                input("\nPremi INVIO per tornare al menu...")
                continue

            # Selezione ordine
            while True:
                sel = input("\nNumero ordine da spedire (0 torna al menu): ").strip()
                if sel == '0':
                    skip_standard_flow = True # Salta il resto e...
                    break # ...esce dal while di selezione
                try:
                    idx = int(sel) - 1
                    if 0 <= idx < len(da_spedire):
                        ordine = da_spedire[idx]
                        order_id = ordine['order_id']
                        destinatario_auto = ordine['destinatario']
                        print(f"\n✅ Selezionato: {ordine['title']}")
                        log.info(f"Selezionato ordine dalla Dashboard: {order_id} ({ordine['buyer']})")
                        break # Esce e prosegue col flusso standard
                    else:
                        print("❌ Numero non valido.")
                except ValueError:
                    print("❌ Inserisci un numero.")
            
            if skip_standard_flow: continue # Torna al menu principale

        # --- OPZIONE 2: MANUALE ---
        elif scelta_iniziale == "2":
            input_ebay = input("Incolla Order ID eBay: ").strip()
            if valido_order_id(input_ebay):
                order_id = input_ebay
                print("✅ Order ID valido.")
            else:
                print("❌ Formato non valido.")
                time.sleep(1)
                continue

        # --- OPZIONE 3: RAPIDA ---
        elif scelta_iniziale == "3":
            pass # Prosegue diretto al flusso standard

        # --- OPZIONE 4: STORICO & PDF (Modificata come richiesto) ---
        elif scelta_iniziale == "4":
            print("\n   ☁️  Scarico storico ShipItalia...")
            lista = get_lista_spedizioni(limit=15)

            if not lista:
                print("❌ Nessuna spedizione trovata.")
                time.sleep(2)
                continue

            print("\n" + "="*100)
            print(f" {'#':<3} | {'TRACKING':<15} | {'DATA':<16} | {'STATO':<12} | {'PDF'}")
            print("="*100)

            for i, sped in enumerate(lista):
                trk = sped.get("trackingCode", "N.D.")
                raw_date = sped.get("createdAt", "")[:16].replace("T", " ")
                stato = sped.get("status", "N.D.")
                has_pdf = "📥 SI" if sped.get("labelUrl") else "   NO"
                print(f" {i+1:<3} | {trk:<15} | {raw_date:<16} | {stato:<12} | {has_pdf}")

            print("-" * 100)

            # Loop di selezione (interno allo storico)
            while True:
                sel = input("\nScegli numero per DETTAGLI/PDF (0 Menu): ").strip()
                if sel == '0': break # Esce dal while e torna al menu principale
                
                try:
                    idx = int(sel) - 1
                    if 0 <= idx < len(lista):
                        scelta = lista[idx]
                        trk = scelta.get("trackingCode")
                        log.info(f"Utente consulta dettagli storico: {trk}")
                        pdf_url = scelta.get("labelUrl")
                        
                        print(f"\n📦 Tracking: {trk}")
                        print(f"   Stato: {scelta.get('status')}")
                        print(f"   Peso:  {scelta.get('weight')} kg")
                        
                        if pdf_url:
                            risp = input("   Vuoi riscaricare il PDF? (S/N): ").lower()
                            if risp == 's':
                                scarica_pdf(pdf_url, trk)
                                print("   ✅ Fatto.")
                                time.sleep(1) # Un secondo per leggere "Fatto"
                        else:
                            print("   ⚠️  PDF non disponibile.")
                        break 
                    else:
                        print("❌ Numero non valido.")
                except ValueError:
                    print("❌ Inserisci un numero.")
            
            continue # Torna al while True principale (Menu)

        # --- CATTURA INPUT NON VALIDI ---
        else:
            print("❌ Scelta non valida.")
            time.sleep(1)
            continue
        
        try:
            peso = chiedi_peso()
            mittente = carica_mittente()
            
            if destinatario_auto:
                destinatario = destinatario_auto
            else:
                destinatario = chiedi_destinatario()

            sconto = chiedi_codice_sconto()

            payload = {
                "weight": peso,
                "sender": mittente,
                "recipient": destinatario,
            }
            if sconto: payload["discountCode"] = sconto

            # Conferma
            while True:
                stampa_riepilogo(payload, order_id)
                if conferma_operazione(): break
                else: gestisci_modifiche(payload)

            # Generazione
            print("\n⏳ Generazione in corso...")
            result = genera_etichetta(payload)
            tracking = result["trackingCode"]
            
            print(f"✅ Etichetta creata: {tracking}")
            log.successo(f"Etichetta creata: {tracking}")

            if order_id:
                gestisci_ordine_ebay(order_id, tracking)

            print("\n✅ Operazione conclusa con successo!")
            input("Premi INVIO per tornare al menu...") # Qui serve per vedere il risultato prima di pulire lo schermo

        except Exception as e:
            print(f"❌ Errore durante il processo: {e}")
            log.errore(f"Errore processo creazione: {e}")
            input("Premi INVIO per continuare...")

if __name__ == "__main__":
    main()
