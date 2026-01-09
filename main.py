import time
import webbrowser
import traceback
from datetime import datetime

# Moduli interni
from config import validate_config
from logger import log
from utils import valido_order_id, genera_link_tracking
from check_token import check_scadenza_token_silenzioso

# Nuova gestione UI
import ui

# Logica di business
from input_utils import (
    chiedi_peso, carica_mittente, chiedi_destinatario,
    chiedi_codice_sconto, stampa_riepilogo,
    conferma_operazione, gestisci_modifiche
)
from shipitalia import genera_etichetta, get_lista_spedizioni
from ebay import gestisci_ordine_ebay, scarica_lista_ordini
from history import salva_in_storico, leggi_storico_locale

def _carica_ordini(cache_ordini, last_update, giorni=30):
    if cache_ordini is None:
        print("\n[INFO] Scarico ordini da eBay...")
        da_spedire, in_viaggio = scarica_lista_ordini(giorni)
        cache_ordini = {"da_spedire": da_spedire, "in_viaggio": in_viaggio}
        last_update = datetime.now()
    return cache_ordini, last_update

def _rimuovi_da_cache(cache_ordini, order_id):
    if not cache_ordini or not order_id:
        return False
    da_spedire = cache_ordini.get("da_spedire") or []
    before = len(da_spedire)
    cache_ordini["da_spedire"] = [o for o in da_spedire if o.get("order_id") != order_id]
    return len(cache_ordini["da_spedire"]) != before

def main():
    log.info("--- Avvio Applicazione ---")

    # 1. Controlli iniziali
    try:
        validate_config()
    except RuntimeError as e:
        ui.avviso_errore(f"CONFIG ERROR: {e}")
        return

    print("[INFO] Controllo token...")
    avviso_token = check_scadenza_token_silenzioso()
    if avviso_token:
        print("\n" + "!" * 60)
        print(avviso_token)
        print("!" * 60 + "\n")
        if "SCADUTO" in avviso_token.upper():
            input("Premi INVIO per uscire...")
            return
        time.sleep(3)

    # --- MEMORIA CACHE (Evita chiamate API continue) ---
    cache_ordini = None
    last_update = None

    # 2. Loop Principale
    while True:
        ui.stampa_header()

        # Info stato cache (Mostra all'utente se i dati sono "freschi" o in memoria)
        if last_update:
            ora_str = last_update.strftime('%H:%M:%S')
            print(f"[INFO] Dati in memoria (Aggiornati alle {ora_str})")

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
            cache_ordini, last_update = _carica_ordini(cache_ordini, last_update, giorni=30)
            da_spedire = cache_ordini["da_spedire"]
            in_viaggio = cache_ordini["in_viaggio"]

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
                    len_ds = len(da_spedire)

                    if 1 <= idx <= len_ds:  # Da Spedire
                        ordine = da_spedire[idx - 1]
                        order_id = ordine['order_id']
                        destinatario_auto = ordine['destinatario']
                        titolo_oggetto = ordine['title']
                        tipo_operazione = "EBAY"
                        print(f"\n[INFO] Selezionato: {titolo_oggetto}")
                        break

                    elif len_ds < idx <= totale:  # In Viaggio
                        ordine = in_viaggio[idx - len_ds - 1]
                        trk = ordine.get('tracking')
                        if trk and trk != "N.D.":
                            webbrowser.open(genera_link_tracking(trk))
                        else:
                            ui.avviso_errore("Tracking non disponibile.")
                    else:
                        ui.avviso_errore("Numero non valido.")
                except ValueError:
                    pass

            if skip_creazione:
                continue

        # --- OPZIONE 2: SPEDISCI DA LISTA (Selezione Rapida) ---
        elif scelta == "2":
            cache_ordini, last_update = _carica_ordini(cache_ordini, last_update, giorni=30)
            da_spedire = cache_ordini["da_spedire"]

            if not da_spedire:
                ui.avviso_info("Nessun ordine da evadere in memoria.")
                # Fallback: se non c'e nulla, offriamo l'inserimento manuale
                risp = input("Vuoi inserire l'ID manualmente? (s/n): ").strip().lower()
                if risp != 's':
                    continue

                input_ebay = input("Incolla Order ID eBay: ").strip()
                if valido_order_id(input_ebay):
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
                        if 1 <= idx <= len(da_spedire):
                            ordine = da_spedire[idx - 1]
                            order_id = ordine['order_id']
                            destinatario_auto = ordine['destinatario']
                            titolo_oggetto = ordine['title']
                            tipo_operazione = "EBAY"
                            print(f"\n[INFO] Selezionato: {titolo_oggetto}")
                            break
                        else:
                            ui.avviso_errore("Numero non valido.")
                    except ValueError:
                        pass

                if skip_creazione:
                    continue

        # --- ETICHETTA RAPIDA (NO EBAY) ---
        elif scelta == "3":
            tipo_operazione = "MANUALE"
            order_id = "MANUALE"
            titolo_oggetto = datetime.now().strftime("Del %d/%m/%Y alle %H:%M")

        # --- STORICO API SHIPITALIA ---
        elif scelta == "4":
            print("\n[INFO] Scarico dati...")
            lista = get_lista_spedizioni(limit=15)
            if not lista:
                ui.avviso_errore("Nessuna spedizione trovata.")
                time.sleep(2)
                continue

            ui.stampa_storico_api(lista)

            while True:
                sel = ui.chiedi_scelta_range(len(lista))
                if sel == '0':
                    break
                try:
                    idx = int(sel) - 1
                    if 0 <= idx < len(lista):
                        ui.stampa_dettaglio_spedizione(idx, lista[idx])
                    else:
                        ui.avviso_errore("Numero non valido.")
                except ValueError:
                    pass
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
            if sconto:
                payload["discountCode"] = sconto

            while True:
                stampa_riepilogo(payload, order_id)
                if conferma_operazione():
                    break
                gestisci_modifiche(payload)

            print("\n[INFO] Generazione in corso...")
            result = genera_etichetta(payload)
            tracking = result["trackingCode"]

            log.successo(f"Creata etichetta: {tracking}")
            print(f"[OK] Etichetta creata: {tracking}")

            salva_in_storico(
                tipo=tipo_operazione,
                destinatario=destinatario.get("name", "N.D."),
                tracking=tracking,
                order_id=order_id,
                titolo=titolo_oggetto
            )
            print("[OK] Salvato nello storico locale.")

            if order_id and valido_order_id(order_id):
                gestisci_ordine_ebay(order_id, tracking)

                # Aggiorniamo la cache: rimuoviamo l'ordine spedito o invalidiamo.
                if cache_ordini and _rimuovi_da_cache(cache_ordini, order_id):
                    last_update = datetime.now()
                    print("[INFO] Cache ordini aggiornata.")
                else:
                    cache_ordini = None
                    last_update = None
                    print("[INFO] Cache ordini invalidata per aggiornamento automatico.")

            elif order_id == "MANUALE":
                print("[INFO] Nessun aggiornamento eBay (Manuale).")

            print("\n[OK] Operazione conclusa!")
            input("Premi INVIO per tornare al menu...")

        except Exception as e:
            ui.avviso_errore(f"Errore processo: {e}")
            log.errore(f"Errore main flow: {e}")
            log.debug(traceback.format_exc())
            input("Premi INVIO...")

if __name__ == "__main__":
    main()
