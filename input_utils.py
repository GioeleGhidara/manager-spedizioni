import re
import ebay
import utils

_MITTENTE_CACHE = None

# --- FUNZIONI DI INPUT ---

def chiedi_peso() -> float:
    while True:
        try:
            valore = input("Peso (kg): ").replace(",", ".")
            return utils.arrotonda_peso_per_eccesso(float(valore))
        except ValueError as e:
            print(f"❌ Errore peso: {e}")

def chiedi_codice_sconto() -> str:
    """Chiede un codice sconto opzionale."""
    codice_default = "SHIPITALIA30"
    scelta = input(
        f"Codice sconto predefinito: {codice_default}. Vuoi cambiarlo? (s/N): "
    ).strip().lower()
    if scelta == "s":
        codice = input("Nuovo codice sconto (INVIO per nessuno): ").strip().upper()
        if codice:
            print(f"   Codice inserito: {codice}")
        return codice
    print(f"   Codice inserito: {codice_default}")
    return codice_default

def parse_indirizzo_blocco(testo: str):
    """Analizza un indirizzo incollato a blocco."""
    if len(testo) > 1000:
        raise ValueError(
            "Indirizzo troppo lungo (max 1000 caratteri). "
            "Rimuovi testo inutile e riprova."
        )

    righe = [r.strip() for r in testo.splitlines() if r.strip()]
    if len(righe) < 2:
        raise ValueError("Indirizzo troppo breve (servono almeno Nome e Via/Città)")

    idx_cap = -1
    dati_citta = {}

    # 1. Cerca la riga del CAP
    for i, riga in enumerate(righe):
        m = re.search(r"(?:\bIT[-\s]?)?(\d{5})\b[\s,]+(.+)", riga, re.IGNORECASE)
        if m:
            idx_cap = i
            dati_citta = {"postalCode": m.group(1), "city": m.group(2).strip().lstrip(",").strip()}
            break
    
    if idx_cap == -1:
        raise ValueError("Non riesco a trovare una riga con CAP valido (5 cifre)")

    # 2. Analizza Parte Superiore (Nome/Indirizzo)
    parte_superiore = righe[:idx_cap]
    if not parte_superiore:
        raise ValueError("Manca il nome o l'indirizzo prima della riga del CAP")

    if len(parte_superiore) == 1:
        unica_riga = parte_superiore[0]
        if any(char.isdigit() for char in unica_riga):
            nome = "N.D."
            indirizzo = unica_riga
        else:
            nome = unica_riga
            indirizzo = "Indirizzo mancante"
    else:
        nome = parte_superiore[0]
        indirizzo = " ".join(parte_superiore[1:])

    # 3. Analizza Parte Inferiore (Telefono)
    telefono = ""
    parte_inferiore = righe[idx_cap+1:]
    
    for riga in parte_inferiore:
        conteggio_numeri = sum(c.isdigit() for c in riga)
        if conteggio_numeri >= 6:
            telefono = utils.normalizza_telefono(riga)
            break 

    return {
        "name": nome,
        "address": indirizzo,
        "postalCode": dati_citta.get("postalCode", ""),
        "city": dati_citta.get("city", ""),
        "phone": telefono,
    }

def chiedi_indirizzo_guidato():
    print(">> Inserimento guidato:")
    return {
        "name": input("   Nome: ").strip(),
        "address": input("   Via: ").strip(),
        "postalCode": input("   CAP: ").strip(),
        "city": input("   Città: ").strip(),
        "phone": utils.normalizza_telefono(input("   Telefono: ").strip()),
    }

def chiedi_indirizzo_libero():
    righe = []
    print("Incolla l'indirizzo (riga vuota per terminare):")
    while True:
        r = input().strip()
        if not r:
            break
        righe.append(r)
    return parse_indirizzo_blocco("\n".join(righe))

def chiedi_destinatario():
    while True:
        print("\n--- DESTINATARIO ---")
        print("1) Incolla indirizzo\n2) Inserimento guidato")
        scelta = input("Scelta (1/2): ").strip()
        try:
            if scelta == "1":
                return chiedi_indirizzo_libero()
            elif scelta == "2":
                return chiedi_indirizzo_guidato()
            else:
                print("Scelta non valida.")
        except Exception as e:
            print(f"❌ Errore nell'inserimento: {e}")

def carica_mittente():
    """Scarica mittente da eBay (o fallback manuale)."""
    global _MITTENTE_CACHE
    print("\n--- MITTENTE ---")

    if _MITTENTE_CACHE:
        print("✓ Mittente in cache:")
        print(f"   {_MITTENTE_CACHE.get('name', 'N.D.')}")
        print(f"   {_MITTENTE_CACHE.get('address', '')}")
        print(f"   {_MITTENTE_CACHE.get('postalCode', '')} {_MITTENTE_CACHE.get('city', '')}")
        scelta = input("\nVuoi usare questo mittente? (S/N): ").strip().lower()
        if scelta != 'n':
            return _MITTENTE_CACHE
    
    # Tentativo automatico eBay
    mittente_ebay = ebay.get_mittente_ebay()
    
    if mittente_ebay:
        # Mostriamo l'indirizzo trovato per conferma
        print("✅ Indirizzo recuperato da eBay:")
        print(f"   {mittente_ebay.get('name', 'N.D.')}")
        print(f"   {mittente_ebay.get('address', '')}")
        print(f"   {mittente_ebay.get('postalCode', '')} {mittente_ebay.get('city', '')}")
        
        scelta = input("\nVuoi usare questo mittente? (S/N): ").strip().lower()
        if scelta != 'n':
            _MITTENTE_CACHE = mittente_ebay
            return mittente_ebay
    else:
        print("⚠️  Impossibile recuperare indirizzo da eBay (o richiesta fallita).")

    print("⚠️  Passiamo all'inserimento manuale.")
    return chiedi_indirizzo_guidato()

# --- FUNZIONI DI OUTPUT (UI) & MODIFICA ---

def stampa_riepilogo(payload, order_id):
    m = payload['sender']
    d = payload['recipient']
    W = 35 

    print("\n" + "=" * (W * 2 + 3))
    print(f"{' 📤 MITTENTE':<{W}} | {' 📥 DESTINATARIO':<{W}}")
    print("-" * (W * 2 + 3))

    nom_m = m.get('name', 'N.D.')[:W-1]
    nom_d = d.get('name', 'N.D.')[:W-1]
    ind_m = m.get('address', '')[:W-1]
    ind_d = d.get('address', '')[:W-1]
    cit_m = f"{m.get('postalCode', '')} {m.get('city', '')}"[:W-1]
    cit_d = f"{d.get('postalCode', '')} {d.get('city', '')}"[:W-1]
    tel_d = d.get('phone', 'Nessuno')[:W-1]
    tel_m = m.get('phone', '')[:W-1]

    print(f"{nom_m:<{W}} | {nom_d:<{W}}")
    print(f"{ind_m:<{W}} | {ind_d:<{W}}")
    print(f"{cit_m:<{W}} | {cit_d:<{W}}")
    print(f"{tel_m:<{W}} | {tel_d:<{W}}")

    print("-" * (W * 2 + 3))
    print(f" ⚖️  PESO: {payload['weight']} kg")
    
    # Mostriamo il codice sconto se c'è
    if payload.get("discountCode"):
        print(f" 🎟️  SCONTO: {payload['discountCode']}")

    if order_id:
        print(f" 🔗 EBAY: ATTIVO (Order ID: {order_id})")
    else:
        print(f" 📄 EBAY: DISATTIVO (Solo creazione PDF)")
        
    print("=" * (W * 2 + 3) + "\n")

def conferma_operazione() -> bool:
    #Ritorna True se l'utente accetta, False se vuole modificare.
    while True:
        risposta = input("Dati corretti? Confermi l'acquisto? (S/N): ").strip().lower()
        if risposta == "s":
            return True
        elif risposta == "n":
            return False

def gestisci_modifiche(payload):
    
    #Menu interattivo per modificare i dati in caso di errore.
    print("\n🔧 MODIFICA DATI")
    print("1) Modifica MITTENTE")
    print("2) Modifica DESTINATARIO")
    print("3) Modifica PESO")
    print("4) Modifica CODICE SCONTO") # Opzione nuova
    print("5) Annulla modifiche (torna al riepilogo)")
    
    scelta = input("Cosa vuoi correggere? (1-5): ").strip()
    
    if scelta == "1":
        print("\n✏️  Reinserisci MITTENTE:")
        payload['sender'] = carica_mittente()
    
    elif scelta == "2":
        print("\n✏️  Reinserisci DESTINATARIO:")
        payload['recipient'] = chiedi_destinatario()
    
    elif scelta == "3":
        print("\n⚖️  Reinserisci PESO:")
        payload['weight'] = chiedi_peso()

    elif scelta == "4":
        print("\n🎟️  Reinserisci SCONTO:")
        payload['discountCode'] = chiedi_codice_sconto()
    
    elif scelta == "5":
        return
    else:
        print("❌ Scelta non valida.")
