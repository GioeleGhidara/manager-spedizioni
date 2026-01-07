import sys
import os
import time

# Imposta encoding per evitare errori su Windows con icone
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from config import validate_config
from logger import log
from utils import valido_order_id
from db_manager import confronta_e_notifica # <--- NUOVO IMPORT
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

    while True:
        pulisci_schermo()
        print("=== SPEDIZIONE MANAGER ===")
        print("\nCosa vuoi fare?")
        print("1) 📋 Dashboard Ordini (Novità & Da Spedire)")
        print("2) ⌨️  Inserisci manualmente Order ID")
        print("3) 🚀 Etichetta rapida (No eBay)")
        print("4) 🔍 Storico Spedizioni & PDF")
        print("0) ❌ Esci")
        
        scelta_iniziale = input("\nScelta (0-4): ").strip()
        if scelta_iniziale: log.info(f"Menu principale: {scelta_iniziale}")
        
        order_id = ""
        destinatario_auto = None
        skip_standard_flow = False 

        if scelta_iniziale == "0":
            print("👋 Alla prossima!")
            break

        # --- OPZIONE 1: DASHBOARD CON NOTIFICHE ---
        elif scelta_iniziale == "1":
            da_spedire, in_viaggio = scarica_lista_ordini(giorni_storico=30)

            # --- BLOCCO NOTIFICHE ---
            tutti = da_spedire + in_viaggio
            notifiche = confronta_e_notifica(tutti)
            
            if notifiche:
                print("\n🔔  NOVITÀ DALL'ULTIMO CONTROLLO:")
                for n in notifiche:
                    print(f"   {n}")
                print("-" * 60)
                input("Premi INVIO per vedere la tabella ordini...")
                pulisci_schermo()
            # ------------------------

            if not da_spedire and not in_viaggio:
                print("\n✅ Nessun ordine attivo (Tutto spedito o vuoto).")
                input("\nPremi INVIO per tornare al menu...")
                continue

            print("\n" + "="*115)
            print(f" {'#':<3} | {'ID ORDINE':<16} | {'DATA':<11} | {'UTENTE':<15} | {'TITOLO OGGETTO'}")
            print("="*115)

            if da_spedire:
                print(" 🔴  DA SPEDIRE (PAGATI)")
                for i, o in enumerate(da_spedire):
                    print(f" {i+1:<3} | {o['order_id'][:16]:<16} | {o['date']:<11} | {o['buyer']:<15} | {o['title']}")
            else:
                print(" ✅  Tutto spedito!")

            print("-" * 115)

            if in_viaggio:
                print(" 🚚  IN VIAGGIO")
                for o in in_viaggio:
                    print(f" {'•':<3} | {o['order_id'][:16]:<16} | {o['shipped_at']:<11} | {o['buyer']:<15} | {o['title']}")
            
            print("="*115)
            
            if not da_spedire:
                input("\nPremi INVIO per tornare al menu...")
                continue

            while True:
                sel = input("\nNumero ordine da spedire (0 torna al menu): ").strip()
                if sel == '0':
                    skip_standard_flow = True 
                    break 
                try:
                    idx = int(sel) - 1
                    if 0 <= idx < len(da_spedire):
                        ordine = da_spedire[idx]
                        order_id = ordine['order_id']
                        destinatario_auto = ordine['destinatario']
                        print(f"\n✅ Selezionato: {ordine['title']}")
                        log.info(f"Selezionato da dashboard: {order_id}")
                        break 
                    else:
                        print("❌ Numero non valido.")
                except ValueError:
                    print("❌ Inserisci un numero.")
            
            if skip_standard_flow: continue 

        elif scelta_iniziale == "2":
            input_ebay = input("Incolla Order ID eBay: ").strip()
            if valido_order_id(input_ebay):
                order_id = input_ebay
                print("✅ Order ID valido.")
            else:
                print("❌ Formato non valido.")
                time.sleep(1)
                continue

        elif scelta_iniziale == "3":
            pass 

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

            while True:
                sel = input("\nScegli numero per DETTAGLI/PDF (0 Menu): ").strip()
                if sel == '0': break 
                
                try:
                    idx = int(sel) - 1
                    if 0 <= idx < len(lista):
                        scelta = lista[idx]
                        trk = scelta.get("trackingCode")
                        pdf_url = scelta.get("labelUrl")
                        
                        print(f"\n📦 Tracking: {trk}")
                        print(f"   Stato: {scelta.get('status')}")
                        print(f"   Peso:  {scelta.get('weight')} kg")
                        
                        if pdf_url:
                            risp = input("   Vuoi riscaricare il PDF? (S/N): ").lower()
                            if risp == 's':
                                scarica_pdf(pdf_url, trk)
                                print("   ✅ Fatto.")
                                time.sleep(1) 
                        else:
                            print("   ⚠️  PDF non disponibile.")
                        break 
                    else:
                        print("❌ Numero non valido.")
                except ValueError:
                    print("❌ Inserisci un numero.")
            
            continue 

        else:
            print("❌ Scelta non valida.")
            time.sleep(1)
            continue
        
        # --- FLUSSO CREAZIONE ETICHETTA ---
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

            while True:
                stampa_riepilogo(payload, order_id)
                if conferma_operazione(): break
                else: gestisci_modifiche(payload)

            print("\n⏳ Generazione in corso...")
            result = genera_etichetta(payload)
            tracking = result["trackingCode"]
            
            print(f"✅ Etichetta creata: {tracking}")
            log.successo(f"Etichetta creata: {tracking}")

            if order_id:
                gestisci_ordine_ebay(order_id, tracking)

            print("\n✅ Operazione conclusa con successo!")
            input("Premi INVIO per tornare al menu...") 

        except Exception as e:
            print(f"❌ Errore durante il processo: {e}")
            log.errore(f"Errore processo creazione: {e}")
            input("Premi INVIO per continuare...")

if __name__ == "__main__":
    main()