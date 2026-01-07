import json
import os
from datetime import datetime
from logger import log

DB_FILE = "storico_locale.json"

def carica_db():
    if not os.path.exists(DB_FILE): return {}
    try:
        with open(DB_FILE, 'r') as f: return json.load(f)
    except: return {}

def salva_db(dati):
    try:
        with open(DB_FILE, 'w') as f: json.dump(dati, f, indent=4)
    except Exception as e: log.errore(f"Errore salvataggio DB: {e}")

def confronta_e_notifica(lista_ordini_aggiornata):
    """
    Confronta lo stato attuale con lo storico e restituisce le notifiche con DATE PRECISE.
    """
    vecchio_db = carica_db()
    nuovo_db = {}
    report = []

    # Mappa rapida per ritrovare l'oggetto ordine dato l'ID
    map_ordini = {o['order_id']: o for o in lista_ordini_aggiornata}

    for o in lista_ordini_aggiornata:
        oid = o['order_id']
        stato_corrente = o.get('status_interno', 'SCONOSCIUTO')
        
        # Salviamo nel DB non solo lo stato, ma anche i dati vitali
        nuovo_db[oid] = {
            "stato": stato_corrente,
            "shipped_at": o.get('shipped_at', '-'),
            "updated_at": datetime.now().strftime("%d/%m %H:%M") # Quando l'abbiamo visto noi
        }

        # --- LOGICA CONFRONTO ---
        if oid not in vecchio_db:
            # È un ordine nuovo
            data_vendita = o['date']
            report.append(f"🆕 NUOVO ORDINE: {o['title'][:25]}... (Del {data_vendita})")
        
        else:
            dati_vecchi = vecchio_db[oid]
            vecchio_stato = dati_vecchi.get("stato")

            if vecchio_stato != stato_corrente:
                # Se è passato a SPEDITO, diciamo QUANDO
                if stato_corrente == "IN_VIAGGIO":
                    data_sped = o.get('shipped_at', 'Oggi')
                    report.append(f"🚀 SPEDITO: {oid} (Il {data_sped})")
                else:
                    report.append(f"🔄 CAMBIO STATO: {oid} -> {stato_corrente}")

    # --- CONTROLLO SPARITI (Consegnati) ---
    for oid, dati_vecchi in vecchio_db.items():
        if oid not in nuovo_db:
            vecchio_stato = dati_vecchi.get("stato")
            if vecchio_stato == "IN_VIAGGIO":
                # Se era in viaggio e non c'è più, è stato consegnato/archiviato
                report.append(f"✅ CONSEGNATO (Archiviato): {oid}")

    salva_db(nuovo_db)
    return report