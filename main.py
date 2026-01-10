import time
from datetime import datetime

import app_logic
import check_token
import config
import ebay
import history
import input_utils
import logger
import services
import shipitalia
import ui
import utils

def main():
    logger.log.info("--- Avvio Applicazione ---")

    # 1. Controlli iniziali
    try:
        config.validate_config()
    except RuntimeError as e:
        ui.avviso_errore(f"CONFIG ERROR: {e}")
        return

    print("⏳ Controllo token...")
    avviso_token = check_token.check_scadenza_token_silenzioso()
    if avviso_token:
        print("\n" + "!" * 60)
        print(avviso_token)
        print("!" * 60 + "\n")
        if "❌" in avviso_token:
            input("Premi INVIO per uscire...")
            return
        time.sleep(3)

    service = services.SpedizioniService(ebay, shipitalia, history)

    # 2. Loop Principale
    while True:
        ui.stampa_header()
        
        # Info stato cache (Mostra all'utente se i dati sono "freschi" o in memoria)
        cache_ts = service.get_cache_last_update()
        if cache_ts:
            ora_str = cache_ts.strftime('%H:%M:%S')
            print(f"⚡ Dati in memoria (Aggiornati alle {ora_str})")
        
        ui.stampa_menu_principale()
        scelta = ui.chiedi_scelta_range(5, label_zero="Uscire")
        
        # Reset variabili per il nuovo giro
        order_id = ""
        titolo_oggetto = ""
        tipo_operazione = "MANUALE"
        destinatario_auto = None
        skip_creazione = False

        if scelta == "0":
            ui.messaggio_uscita()
            break

        # --- OPZIONE 1: DASHBOARD COMPLETA (Overview) ---
        elif scelta == "1":
            # LOGICA CACHE: usa la cache se presente, altrimenti scarica
            da_spedire, in_viaggio = service.carica_ordini_cached(30)

            if not da_spedire and not in_viaggio:
                ui.avviso_info("Nessun ordine attivo trovato.")
                input("\nPremi INVIO...")
                continue

            ui.stampa_dashboard_ebay(da_spedire, in_viaggio)

            totale = len(da_spedire) + len(in_viaggio)
            while True:
                sel = ui.chiedi_scelta_range(totale)
                if sel == '0': 
                    skip_creazione = True
                    break
                
                try:
                    idx = int(sel)
                    action = service.resolve_dashboard(da_spedire, in_viaggio, idx)
                    if action["action"] == "order":
                        ordine = action["order"]
                        order_id = ordine['order_id']
                        destinatario_auto = ordine['destinatario']
                        titolo_oggetto = ordine['title']
                        tipo_operazione = "EBAY"
                        print(f"\nƒo. Selezionato: {titolo_oggetto}")
                        break
                    elif action["action"] == "tracking":
                        tracking_link = utils.genera_link_tracking(action["tracking"])
                        print(f"\n🚚 Tracking: {tracking_link}")
                        input("Premi INVIO per tornare indietro...")
                        continue  
                    ui.avviso_errore("Numero non valido.")
                except ValueError:
                    pass
            
            if skip_creazione: continue

        # --- OPZIONE 2: SPEDISCI DA LISTA (Selezione Rapida) ---
        elif scelta == "2":
            # LOGICA CACHE: usa la cache se presente, altrimenti scarica
            da_spedire, _in_viaggio = service.carica_ordini_cached(30)

            if not da_spedire:
                ui.avviso_info("Nessun ordine da evadere in memoria.")
                # Fallback: se non c'è nulla, offriamo l'inserimento manuale
                risp = input("Vuoi inserire l'ID manualmente? (s/n): ").strip().lower()
                if risp != 's':
                    continue
                
                input_ebay = input("Incolla Order ID eBay: ").strip()
                if utils.valido_order_id(input_ebay):
                    order_id = input_ebay
                    tipo_operazione = "EBAY"
                    titolo_oggetto = "Inserito manualmente"
                else:
                    ui.avviso_errore("ID non valido.")
                    time.sleep(1)
                    continue
            else:
                ui.stampa_lista_selezione_ebay(da_spedire)
                
                while True:
                    sel = ui.chiedi_scelta_range(len(da_spedire))
                    if sel == '0':
                        skip_creazione = True
                        break
                    
                    try:
                        idx = int(sel)
                        action = service.resolve_lista_spedire(da_spedire, idx)
                        if action["action"] == "order":
                            ordine = action["order"]
                            order_id = ordine['order_id']
                            destinatario_auto = ordine['destinatario']
                            titolo_oggetto = ordine['title']
                            tipo_operazione = "EBAY"
                            print(f"\nƒo. Selezionato: {titolo_oggetto}")
                            break
                        ui.avviso_errore("Numero non valido.")
                    except ValueError:
                        pass
                
                if skip_creazione: continue

        # --- ETICHETTA RAPIDA (NO EBAY) ---
        elif scelta == "3":
            tipo_operazione = "MANUALE"
            order_id = "MANUALE"
            titolo_oggetto = datetime.now().strftime("Del %d/%m/%Y alle %H:%M")

        # --- STORICO API SHIPITALIA ---
        elif scelta == "4":
            print("\n   ☁️  Scarico dati...")
            lista = service.lista_spedizioni_cached(limit=15)
            if not lista:
                ui.avviso_errore("Nessuna spedizione trovata.")
                time.sleep(2)
                continue

            ui.stampa_storico_api(lista)
            
            while True:
                sel = ui.chiedi_scelta_range(len(lista))
                if sel == '0': break
                try:
                    idx = int(sel)
                    action = service.resolve_storico_index(lista, idx)
                    if action["action"] == "item":
                        ui.stampa_dettaglio_spedizione(action["index"], action["item"])
                    else:
                        ui.avviso_errore("Numero non valido.")
                except ValueError:
                    pass
            continue

        # --- STORICO LOCALE ---
        elif scelta == "5":
            storico = history.leggi_storico_locale()
            if not storico:
                ui.avviso_errore("Nessuno storico locale.")
                time.sleep(2)
                continue
            
            ui.stampa_storico_locale(storico)
            input("\nPremi INVIO per tornare al menu...")
            continue

        else:
            ui.avviso_errore("Scelta non valida.")
            time.sleep(1)
            continue

        # ==========================================
        #       FLUSSO CREAZIONE ETICHETTA
        # ==========================================
        try:
            peso = input_utils.chiedi_peso()
            mittente = input_utils.carica_mittente()
            destinatario = destinatario_auto if destinatario_auto else input_utils.chiedi_destinatario()
            sconto = input_utils.chiedi_codice_sconto()

            payload = app_logic.build_payload(peso, mittente, destinatario, sconto)

            while True:
                input_utils.stampa_riepilogo(payload, order_id)
                if input_utils.conferma_operazione(): break
                input_utils.gestisci_modifiche(payload)

            print("\n⏳ Generazione in corso...")
            result = service.crea_etichetta(payload)
            tracking = result["trackingCode"]

            logger.log.successo(f"Creata etichetta: {tracking}")
            print(f"✅ Etichetta creata: {tracking}")

            service.salva_storico(
                tipo=tipo_operazione,
                destinatario=destinatario.get("name", "N.D."),
                tracking=tracking,
                order_id=order_id,
                titolo=titolo_oggetto
            )
            print("💾 Salvato nello storico locale.")

            service.invalida_ship_cache()
            if order_id and utils.valido_order_id(order_id):
                service.aggiorna_tracking_ebay(order_id, tracking)
                
                # IMPORTANTE: Invalidiamo la cache dopo aver spedito un ordine eBay.
                # Così al prossimo giro la lista si aggiorna e l'ordine sparisce.
                service.invalida_cache()
                print("🔄 Lista ordini invalidata per aggiornamento automatico.")

            elif order_id == "MANUALE":
                print("ℹ️  Nessun aggiornamento eBay (Manuale).")

            print("\n✅ Operazione conclusa!")
            input("Premi INVIO per tornare al menu...")

        except Exception as e:
            ui.avviso_errore(f"Errore processo: {e}")
            logger.log.errore(f"Errore main flow: {e}")
            input("Premi INVIO...")

if __name__ == "__main__":
    main()
