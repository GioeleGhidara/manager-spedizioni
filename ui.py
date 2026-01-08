import os
import sys

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
    print("2) 📦 Spedisci da Lista (eBay)") 
    print("3) 🚀 Etichetta rapida")
    print("4) 🔍 Storico ShipItalia (PDF e API)")
    print("5) 📒 Storico Locale (Dettagliato)")
    print("0) ❌ Esci")

def chiedi_scelta_range(max_val):
    """
    Chiede input all'utente mostrando il range disponibile.
    """
    if max_val > 1:
        prompt = f"\nScegli opzione (1-{max_val}) o 0 per Menu: "
    elif max_val == 1:
        prompt = f"\nScegli opzione (1) o 0 per Menu: "
    else:
        prompt = "\nNessuna opzione disponibile. Premi 0 per Menu: "
    
    return input(prompt).strip()

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

# --- NUOVA FUNZIONE PER OPZIONE 2 ---
def stampa_lista_selezione_ebay(da_spedire):
    """
    Stampa una tabella semplificata solo per la selezione 'Da Spedire'.
    """
    if not da_spedire:
        print("\n✅ Nessun ordine in attesa di spedizione.")
        return

    print(f"\n📦 TROVATI {len(da_spedire)} ORDINI DA EVADERE:")
    print("=" * 100)
    print(f" {'#':<3} | {'DATA':<11} | {'UTENTE':<15} | {'TITOLO OGGETTO'}")
    print("=" * 100)

    for i, o in enumerate(da_spedire):
        titolo = o['title'][:55] + ".." if len(o['title']) > 55 else o['title']
        print(f" {i+1:<3} | {o['date']:<11} | {o['buyer']:<15} | {titolo}")
    
    print("-" * 100)
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

def stampa_dettaglio_spedizione(idx, spedizione):
    trk = spedizione.get("trackingCode")
    pdf_url = spedizione.get("labelUrl", "Non disponibile")
    url_poste = f"https://www.poste.it/cerca/#/risultati-spedizioni/{trk}"

    print(f"\n📦 DETTAGLI SPEDIZIONE #{idx+1}")
    print(f"   Tracking:    {url_poste}")
    print(f"   Scarica PDF: {pdf_url}")
    print("\n(Copia il link o usa CTRL+Click se supportato)")

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