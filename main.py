import time
import webbrowser
from datetime import datetime

# Moduli interni
from config import validate_config
from logger import log
from utils import valido_order_id
from check_token import check_scadenza_token_silenzioso

# Nuova gestione UI
import ui

# Logica di business
from input_utils import (
    chiedi_peso, carica_mittente, chiedi_destinatario, 
    chiedi_codice_sconto, stampa_riepilogo, 
    conferma_operazione, gestisci_modifiche
)
from shipitalia import genera_etichetta, get_lista_spedizioni, scarica_pdf
from ebay import gestisci_ordine_ebay, scarica_lista_ordini
from history import salva_in_storico, leggi_storico_locale

def main():
    log.info("--- Avvio Applicazione ---")

    # 1. Controlli iniziali
    try:
        validate_config()
    except RuntimeError as e:
        ui.avviso_errore(f"CONFIG ERROR: {e}")
        return

    print("⏳ Avvio sistema...")
    avviso_token = check_scadenza_token_silenzioso()
    if avviso_token:
        print("\n" + "!" * 60)
        print(avviso_token)
        print("!" * 60 + "\n")
        if "❌" in avviso_token:
            input("Premi INVIO per uscire...")
            return
        time.sleep(3)

    # 2. Loop Principale
    while True:
        ui.stampa_header()
        ui.stampa_menu_principale()
        
        scelta = input("\nScelta (0-5): ").strip()
        
        # Reset variabili per il nuovo giro
        order_id = ""
        titolo_oggetto = ""
        tipo_operazione = "MANUALE"
        destinatario_auto = None
        skip_creazione = False

        if scelta == "0":
            ui.messaggio_uscita()
            break

        # --- DASHBOARD EBAY ---
        elif scelta == "1":
            da_spedire, in_viaggio = scarica_lista_ordini(30)
            
            if not da_spedire and not in_viaggio:
                ui.avviso_info("Nessun ordine attivo.")
                input("\nPremi INVIO...")
                continue

            ui.stampa_dashboard_ebay(da_spedire, in_viaggio)

            while True:
                sel = input("\nNumero ordine (0 Menu): ").strip()
                if sel == '0': 
                    skip_creazione = True
                    break
                
                try:
                    idx = int(sel)
                    len_ds = len(da_spedire)
                    
                    # Selezione "Da Spedire"
                    if 1 <= idx <= len_ds:
                        ordine = da_spedire[idx - 1]
                        order_id = ordine['order_id']
                        destinatario_auto = ordine['destinatario']
                        titolo_oggetto = ordine['title']
                        tipo_operazione = "EBAY"
                        print(f"\n✅ Selezionato: {titolo_oggetto}")
                        break
                    
                    # Selezione "In Viaggio"
                    elif len_ds < idx <= (len_ds + len(in_viaggio)):
                        ordine = in_viaggio[idx - len_ds - 1]
                        trk = ordine.get('tracking')
                        if trk and trk != "N.D.":
                            webbrowser.open(f"https://www.poste.it/cerca/#/risultati-spedizioni/{trk}")
                        else:
                            ui.avviso_errore("Tracking non disponibile.")
                    else:
                        ui.avviso_errore("Numero non valido.")
                except ValueError:
                    pass
            
            if skip_creazione: continue

        # --- INSERIMENTO MANUALE ID ---
        elif scelta == "2":
            input_ebay = input("Incolla Order ID eBay: ").strip()
            if valido_order_id(input_ebay):
                order_id = input_ebay
                tipo_operazione = "EBAY"
                titolo_oggetto = "Inserito manualmente"
            else:
                ui.avviso_errore("Formato ID non valido.")
                time.sleep(1)
                continue

        # --- ETICHETTA RAPIDA ---
        elif scelta == "3":
            tipo_operazione = "MANUALE"
            order_id = "MANUALE"
            titolo_oggetto = datetime.now().strftime("Del %d/%m/%Y alle %H:%M")

        # --- STORICO API SHIPITALIA ---
        elif scelta == "4":
            print("\n   ☁️  Scarico dati...")
            lista = get_lista_spedizioni(limit=15)
            if not lista:
                ui.avviso_errore("Nessuna spedizione trovata.")
                time.sleep(2)
                continue

            ui.stampa_storico_api(lista)

            while True:
                sel = input("\nQuale spedizione vuoi vedere? (0 Menu): ").strip()
                if sel == '0': break
                try:
                    idx = int(sel) - 1
                    if 0 <= idx < len(lista):
                        ui.stampa_dettaglio_spedizione(idx, lista[idx])
                    else:
                        ui.avviso_errore("Numero non valido.")
                except ValueError: pass
            continue

        # --- STORICO LOCALE ---
        elif scelta == "5":
            storico = leggi_storico_locale()
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
            peso = chiedi_peso()
            mittente = carica_mittente()
            destinatario = destinatario_auto if destinatario_auto else chiedi_destinatario()
            sconto = chiedi_codice_sconto()

            payload = {
                "weight": peso,
                "sender": mittente,
                "recipient": destinatario
            }
            if sconto: payload["discountCode"] = sconto

            while True:
                stampa_riepilogo(payload, order_id)
                if conferma_operazione(): break
                gestisci_modifiche(payload)

            print("\n⏳ Generazione in corso...")
            result = genera_etichetta(payload)
            tracking = result["trackingCode"]

            log.successo(f"Creata etichetta: {tracking}")
            print(f"✅ Etichetta creata: {tracking}")

            salva_in_storico(
                tipo=tipo_operazione,
                destinatario=destinatario.get("name", "N.D."),
                tracking=tracking,
                order_id=order_id,
                titolo=titolo_oggetto
            )
            print("💾 Salvato nello storico locale.")

            if order_id and valido_order_id(order_id):
                gestisci_ordine_ebay(order_id, tracking)
            elif order_id == "MANUALE":
                print("ℹ️  Nessun aggiornamento eBay (Manuale).")

            print("\n✅ Operazione conclusa!")
            input("Premi INVIO per tornare al menu...")

        except Exception as e:
            ui.avviso_errore(f"Errore processo: {e}")
            log.errore(f"Errore main flow: {e}")
            input("Premi INVIO...")

if __name__ == "__main__":
    main()