import os
import sys
import utils

# Imposta encoding per Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# ------------------------------------

def pulisci_schermo():
    os.system('cls' if os.name == 'nt' else 'clear')

# ------------------------------------

def stampa_header():
    pulisci_schermo()
    print("=== SPEDIZIONE MANAGER ===")

# ------------------------------------

def stampa_menu_principale():
    print("\nCosa vuoi fare?")
    print("1) 📦 Dashboard Ordini (eBay)")
    print("2) 📄 Spedisci da Lista (eBay)")
    print("3) ⚡ Etichetta rapida")
    print("4) 📚 Storico ShipItalia (PDF e API)")
    print("5) 🗂️  Storico Locale (Dettagliato)")
    print("0) ❌ Esci")

# ------------------------------------

def chiedi_scelta_range(max_val, label_zero="Menu"):
    if max_val > 1:
        prompt = f"\nScegli opzione (1-{max_val}) o 0 per {label_zero}: "
    elif max_val == 1:
        prompt = f"\nScegli opzione (1) o 0 per {label_zero}: "
    else:
        prompt = f"\nNessuna opzione disponibile. Premi 0 per {label_zero}: "
    
    return input(prompt).strip()

# ------------------------------------

def stampa_dashboard_ebay(ordini, cambiamenti=None):
    if not ordini and not cambiamenti:
        print("\nNessun ordine attivo trovato.")
        return

    if cambiamenti is None:
        cambiamenti = []

    width = 150
    w_idx = 3
    w_id = 14
    w_data = 11
    w_utente = 15
    w_tracking = 15
    w_stato = 18
    w_pos = 18
    w_titolo = 40

    def _trunca(val, max_len):
        s = str(val) if val is not None else ""
        if len(s) > max_len:
            return s[: max_len - 2] + ".."
        return s

    header = (
        f" {'#':<{w_idx}} | {'DATA':<{w_data}} | {'UTENTE':<{w_utente}} | "
        f"{'STATO':<{w_stato}} | {'POSIZIONE':<{w_pos}} | {'TITOLO':<{w_titolo}}"
    )
    print("\n" + "=" * width)
    print(header)

    label_stato = {
        'DA SPEDIRE': '📦 DA SPEDIRE',
        'ETICHETTA CREATA': '🏷️  ETICHETTA CREATA',
        'IN TRANSITO': '🚚 IN TRANSITO',
        'CONSEGNATO': '✅ CONSEGNATO',
    }
    label_tabella = {
        'DA SPEDIRE': '📦 DA SPEDIRE',
        'ETICHETTA CREATA': '🏷️  ETICHETTA',
        'IN TRANSITO': '🚚 IN TRANSITO',
        'CONSEGNATO': '✅ CONSEGNATO',
    }

    def _stampa_cambiamenti(lista):
        if not lista:
            return
        for c in lista:
            da = label_tabella.get(c.get('from_status', ''), c.get('from_status', '')).lower()
            a = label_tabella.get(c.get('to_status', ''), c.get('to_status', '')).lower()
            titolo_riga = _trunca(c.get('title', ''), w_titolo)
            if c.get('to_status') == 'CONSEGNATO':
                print(f"-> {titolo_riga} consegnato, controlla lo stato del pagamento")
            else:
                print(f"-> aggiornamento: {titolo_riga} passato da {da} a {a}")

    gruppi = {'DA SPEDIRE': [], 'ETICHETTA CREATA': [], 'IN TRANSITO': []}
    for ordine in ordini:
        stato = ordine.get('dashboard_status', '')
        gruppi.setdefault(stato, []).append(ordine)

    idx = 1
    for stato in ('DA SPEDIRE', 'ETICHETTA CREATA', 'IN TRANSITO'):
        lista = gruppi.get(stato, [])
        cambiamenti_stato = [c for c in cambiamenti if c.get('to_status') == stato]
        if not lista and not cambiamenti_stato:
            continue
        print("=" * width)
        print(f"{label_stato.get(stato, stato)}")
        if cambiamenti_stato:
            _stampa_cambiamenti(cambiamenti_stato)
        if not lista:
            print('Nessun ordine in questo stato.')
            continue
        for o in lista:
            data = _trunca(o.get('date', ''), w_data)
            utente = _trunca(o.get('buyer', ''), w_utente)
            posizione = _trunca(o.get('dashboard_posizione', ''), w_pos)
            titolo = _trunca(o.get('title', ''), w_titolo)
            stato_cell = label_tabella.get(stato, stato)
            print(
                f" {idx:<{w_idx}} | {data:<{w_data}} | {utente:<{w_utente}} | "
                f"{stato_cell:<{w_stato}} | {posizione:<{w_pos}} | {titolo:<{w_titolo}}"
            )
            idx += 1

    cambiamenti_consegnato = [c for c in cambiamenti if c.get('to_status') == 'CONSEGNATO']
    if cambiamenti_consegnato:
        print("=" * width)
        print('\u2705 CONSEGNATO')
        _stampa_cambiamenti(cambiamenti_consegnato)

    print("=" * width)

# ------------------------------------

def stampa_storico_api(lista):
    print("\n" + "=" * 75)
    print(f" {'#':<3} | {'TRACKING':<15} | {'DATA':<16} | {'STATO':<12} | {'PDF'}")
    print("=" * 75)

    for i, sped in enumerate(lista):
        trk = sped.get("trackingCode", "N.D.")
        raw_date = sped.get("createdAt", "")[:16].replace("T", " ")
        stato = sped.get("status", "N.D.")
        has_pdf = "📥 Si" if sped.get("labelUrl") else "   No"
        
        print(f" {i+1:<3} | {trk:<15} | {raw_date:<16} | {stato:<12} | {has_pdf}")

    print("-" * 75)

# ------------------------------------

def stampa_dettaglio_spedizione(idx, spedizione):
    trk = spedizione.get("trackingCode")
    pdf_url = spedizione.get("labelUrl", "Non disponibile")
    url_poste = utils.genera_link_tracking(trk)
    print(f"\n📦 DETTAGLI SPEDIZIONE #{idx+1}")
    print(f"   Tracking:    {url_poste}")
    print(f"   Scarica PDF: {pdf_url}")
    print("\n(Copia il link o usa CTRL+Click se supportato)")
    
# ------------------------------------

def stampa_storico_locale(storico):
    print("\n" + "=" * 110)
    print(f" {'DATA':<16} | {'DESTINATARIO':<20} | {'TRACKING':<15} | {'TITOLO'}")
    print("=" * 110)
    
    for s in storico:
        dest = s['destinatario'][:19]
        tit = s['titolo'][:40]
        print(f" {s['data']:<16} | {dest:<20} | {s['tracking']:<15} | {tit}")
    print("=" * 110)

# ------------------------------------

def messaggio_uscita():
    print("👋 Alla prossima!")

# ------------------------------------

def avviso_errore(msg):
    print(f"❌ {msg}")

# ------------------------------------

def avviso_info(msg):
    print(f"ℹ️  {msg}")

# ------------------------------------

def stampa_dettagli_poste_completi(tracking, dati_json):
    if not dati_json:
        print(f"❌ Nessun dato trovato per {tracking}")
        return

    prodotto = dati_json.get('tipoProdotto', 'Spedizione')
    prevista = dati_json.get('dataPrevistaConsegna', '')
    
    print(f"\n📦 TRACKING POSTE: {tracking}")
    print(f"   Prodotto: {prodotto}")
    if prevista:
        print(f"   📅 Previsione: {prevista}")
    
    print("\n   --- STORIA MOVIMENTI ---")
    movimenti = dati_json.get("listaMovimenti", [])
    
    # Li stampiamo dal più recente al più vecchio (invertendo la lista)
    for mov in reversed(movimenti):
        stato = mov.get("statoLavorazione", "")
        luogo = mov.get("luogo", "").title() # .title() rende Maiuscole Le Iniziali
        ts = mov.get("dataOra")
        
        data_str = "??/?? ??:??"
        if ts:
            dt = utils.datetime.fromtimestamp(ts / 1000)
            data_str = dt.strftime("%d/%m %H:%M")
            
        print(f"   🔹 {data_str} | {stato}")
        if luogo:
            print(f"       📍 {luogo}")
            
    print("")
