import os
import sys
import webbrowser

# Imposta encoding per Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def pulisci_schermo():
    os.system('cls' if os.name == 'nt' else 'clear')

def stampa_header():
    pulisci_schermo()
    print("=== SPEDIZIONE MANAGER ===")

def stampa_menu_principale():
    print("\nCosa vuoi fare?")
    print("1) 📋 Dashboard Ordini (eBay)")
    print("2) ⌨️  Inserisci Order ID")
    print("3) 🚀 Etichetta rapida (No eBay)")
    print("4) 🔍 Storico ShipItalia (PDF e API)")
    print("5) 📒 Storico Locale (Dettagliato)")
    print("0) ❌ Esci")

def stampa_dashboard_ebay(da_spedire, in_viaggio):
    print("\n" + "=" * 120)
    print(f" {'#':<3} | {'ID ORDINE':<14} | {'DATA':<11} | {'UTENTE':<15} | {'TRACKING / STATO':<18} | {'TITOLO OGGETTO'}")
    print("=" * 120)

    # DA SPEDIRE
    if da_spedire:
        print(" 🔴  DA SPEDIRE")
        for i, o in enumerate(da_spedire):
            print(f" {i+1:<3} | {o['order_id'][:14]:<14} | {o['date']:<11} | {o['buyer']:<15} | {'DA SPEDIRE':<18} | {o['title']}")
    else:
        print(" ✅  Tutto spedito!")

    print("-" * 120)

    # IN VIAGGIO
    if in_viaggio:
        print(" 🚚  IN VIAGGIO")
        start_idx = len(da_spedire) + 1
        for i, o in enumerate(in_viaggio):
            idx = start_idx + i
            trk_display = o.get('tracking', 'N.D.')
            print(f" {idx:<3} | {o['order_id'][:14]:<14} | {o['shipped_at']:<11} | {o['buyer']:<15} | {trk_display:<18} | {o['title']}")

    print("=" * 120)

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

def stampa_dettaglio_spedizione(idx, spedizione):
    trk = spedizione.get("trackingCode")
    pdf_url = spedizione.get("labelUrl", "Non disponibile")
    url_poste = f"https://www.poste.it/cerca/#/risultati-spedizioni/{trk}"

    print(f"\n📦 DETTAGLI SPEDIZIONE #{idx+1}")
    print(f"   Tracking:    {url_poste}")
    print(f"   Scarica PDF: {pdf_url}")
    print("\n(Fai CTRL+Click sui link qui sopra per aprirli)")

def stampa_storico_locale(storico):
    print("\n" + "=" * 110)
    print(f" {'DATA':<16} | {'DESTINATARIO':<20} | {'TRACKING':<15} | {'TITOLO'}")
    print("=" * 110)
    
    for s in storico:
        dest = s['destinatario'][:19]
        tit = s['titolo'][:40]
        print(f" {s['data']:<16} | {dest:<20} | {s['tracking']:<15} | {tit}")
    print("=" * 110)

def messaggio_uscita():
    print("👋 Alla prossima!")

def avviso_errore(msg):
    print(f"❌ {msg}")

def avviso_info(msg):
    print(f"ℹ️  {msg}")