import json
import os
from datetime import datetime

FILE_STORICO = "storico_spedizioni.json"

def salva_in_storico(tipo, destinatario, tracking, order_id=None, titolo=None):
    """
    Salva una nuova spedizione nel file JSON locale.
    """
    # 1. Carica esistente
    lista = []
    if os.path.exists(FILE_STORICO):
        try:
            with open(FILE_STORICO, "r", encoding="utf-8") as f:
                lista = json.load(f)
        except:
            lista = []

    # 2. Prepara il nuovo oggetto
    nuovo_elemento = {
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "tipo": tipo,  # "EBAY" o "MANUALE"
        "destinatario": destinatario,
        "tracking": tracking,
        "order_id": order_id if order_id else "-",
        "titolo": titolo if titolo else "-"
    }

    # 3. Aggiungi in cima alla lista
    lista.insert(0, nuovo_elemento)

    # 4. Salva (tieni solo gli ultimi 500 per non appesantire)
    try:
        with open(FILE_STORICO, "w", encoding="utf-8") as f:
            json.dump(lista[:500], f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"⚠️ Errore salvataggio storico locale: {e}")
        return False

def leggi_storico_locale():
    """Ritorna la lista delle spedizioni salvate localmente."""
    if not os.path.exists(FILE_STORICO):
        return []
    try:
        with open(FILE_STORICO, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []