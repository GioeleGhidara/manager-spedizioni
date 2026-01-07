import sys
import os
import time
import webbrowser

# Imposta encoding per evitare errori su Windows con icone
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from config import validate_config
from logger import log
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
        print("1) 📋 Dashboard Ordini (eBay)")
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

        # --- OPZIONE 1: DASHBOARD INTERATTIVA ---
        elif scelta_iniziale == "1":
            da_spedire, in_viaggio = scarica_lista_ordini(giorni_storico=30)

            if not da_spedire and not in_viaggio:
                print("\n✅ Nessun ordine attivo (Tutto spedito o vuoto).")
                input("\nPremi INVIO per tornare al menu...")
                continue

            # Creiamo una numerazione continua
            # Esempio: 1..3 sono da spedire, 4..6 sono in viaggio
            count_da_spedire = len(da_spedire)
            count_in_viaggio = len(in_viaggio)
            
            print("\n" + "="*120)
            print(f" {'#':<3} | {'ID ORDINE':<14} | {'DATA':<11} | {'UTENTE':<15} | {'TRACKING / STATO':<18} | {'TITOLO OGGETTO'}")
            print("="*120)

            # --- SEZIONE DA SPEDIRE ---
            if da_spedire:
                print(" 🔴  DA SPEDIRE")
                for i, o in enumerate(da_spedire):
                    idx = i + 1
                    print(f" {idx:<3} | {o['order_id'][:14]:<14} | {o['date']:<11} | {o['buyer']:<15} | {'DA SPEDIRE':<18} | {o['title']}")
            else:
                print(" ✅  Tutto spedito!")

            print("-" * 120)

            # --- SEZIONE IN VIAGGIO ---
            if in_viaggio:
                print(" 🚚  IN VIAGGIO")
                for i, o in enumerate(in_viaggio):
                    idx = count_da_spedire + i + 1
                    trk_display = o.get('tracking', 'N.D.')
                    print(f" {idx:<3} | {o['order_id'][:14]:<14} | {o['shipped_at']:<11} | {o['buyer']:<15} | {trk_display:<18} | {o['title']}")
            
            print("="*120)
            
            while True:
                prompt_msg = "\nNumero ordine (per Spedire o Tracciare, 0 Menu): "
                sel = input(prompt_msg).strip()
                
                if sel == '0':
                    skip_standard_flow = True 
                    break 
                
                try:
                    idx_scelto = int(sel)
                    
                    # CASO 1: Selezione "DA SPEDIRE"
                    if 1 <= idx_scelto <= count_da_spedire:
                        idx_array = idx_scelto - 1
                        ordine = da_spedire[idx_array]
                        order_id = ordine['order_id']
                        destinatario_auto = ordine['destinatario']
                        print(f"\n✅ Selezionato per SPEDIZIONE: {ordine['title']}")
                        log.info(f"Selezionato da dashboard (Spedizione): {order_id}")
                        break # Esce dal loop e va al flusso creazione etichetta
                    
                    # CASO 2: Selezione "IN VIAGGIO"
                    elif count_da_spedire < idx_scelto <= (count_da_spedire + count_in_viaggio):
                        idx_array = idx_scelto - count_da_spedire - 1
                        ordine = in_viaggio[idx_array]
                        trk = ordine.get('tracking')
                        
                        if trk and trk != "N.D.":
                            url = f"https://www.poste.it/cerca/#/risultati-spedizioni/{trk}"
                            print(f"\n   🌍 Apro tracking Poste: {trk}")
                            webbrowser.open(url)
                        else:
                            print("\n   ⚠️  Tracking non disponibile o formato non valido.")
                        
                        # Non facciamo break qui, rimaniamo nella dashboard così puoi cliccarne altri
                    
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

        # --- OPZIONE 4: STORICO ---
        elif scelta_iniziale == "4":
            print("\n   ☁️  Scarico storico ShipItalia...")
            lista = get_lista_spedizioni(limit=15)

            if not lista:
                print("❌ Nessuna spedizione trovata.")
                time.sleep(2)
                continue

            # --- TABELLA RIEPILOGATIVA ---
            print("\n" + "="*95)
            print(f" {'#':<3} | {'TRACKING':<15} | {'DATA':<16} | {'STATO':<12} | {'PDF'}")
            print("="*95)

            for i, sped in enumerate(lista):
                trk = sped.get("trackingCode", "N.D.")
                # Data formattata più pulita
                raw_date = sped.get("createdAt", "")[:16].replace("T", " ") 
                stato = sped.get("status", "N.D.")
                has_pdf = "📥 SI" if sped.get("labelUrl") else "   NO"
                print(f" {i+1:<3} | {trk:<15} | {raw_date:<16} | {stato:<12} | {has_pdf}")

            print("-" * 95)

            # --- SELEZIONE E AZIONI ---
            while True:
                sel = input("\nScegli numero per DETTAGLI (0 Menu): ").strip()
                if sel == '0': break 
                
                try:
                    idx = int(sel) - 1
                    if 0 <= idx < len(lista):
                        scelta = lista[idx]
                        trk = scelta.get("trackingCode")
                        pdf_url = scelta.get("labelUrl")
                        
                        # URL Poste Italiane dinamico
                        url_poste = f"https://www.poste.it/cerca/#/risultati-spedizioni/{trk}"
                        
                        print(f"\n📦 DETTAGLI SPEDIZIONE")
                        print(f"   Tracking: {trk}")
                        print(f"   Stato:    {scelta.get('status')}")
                        print(f"   Peso:     {scelta.get('weight')} kg")
                        print(f"   Link:     {url_poste}")
                        
                        # --- LOOP SOTTO-MENU AZIONI ---
                        while True:
                            print("\n   [T] 🌍 Apri Tracking Poste  |  [P] 📥 Scarica PDF  |  [INVIO] Indietro")
                            azione = input("   Cosa vuoi fare? ").strip().lower()

                            if azione == 't':
                                print(f"   🚀 Apro il browser su Poste.it...")
                                webbrowser.open(url_poste)
                            
                            elif azione == 'p':
                                if pdf_url:
                                    scarica_pdf(pdf_url, trk)
                                    print("   ✅ PDF scaricato/aperto.")
                                else:
                                    print("   ⚠️  PDF non disponibile per questa spedizione.")
                            
                            else:
                                break 
                    else:
                        print("❌ Numero non valido.")
                except ValueError:
                    print("❌ Inserisci un numero.")
            
            # Torna al menu principale dopo aver finito con lo storico
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