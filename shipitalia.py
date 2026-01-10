import os
import re
import webbrowser
import copy
import config
import logger
import utils

def _prepara_payload_sicuro(payload):
    """
    Rende il payload più "sicuro" per l'API.
    Pulisce spazi e tronca i testi troppo lunghi.
    """
    p = copy.deepcopy(payload) if payload is not None else {}
    for role in ['sender', 'recipient']:
        if role in p and isinstance(p[role], dict):
            # MIGLIORIA: Facciamo strip() PRIMA di tagliare a 40 caratteri.
            # Così se c'è spazio all'inizio, non perdiamo lettere del nome.
            p[role]['name'] = str(p[role].get('name', '')).strip()[:40]
            p[role]['address'] = str(p[role].get('address', '')).strip()[:40]
            p[role]['city'] = str(p[role].get('city', '')).strip()[:36]
            # Il cap lo limitiamo a 10 per sicurezza
            if 'postalCode' in p[role]:
                p[role]['postalCode'] = str(p[role].get('postalCode', '')).strip()[:10]
    return p

@logger.traccia
def get_lista_spedizioni(limit=10):
    """
    Scarica la lista delle ultime spedizioni.
    Gestisce la struttura {data: {shipments: [...]}} scoperta col test.
    """
    session = utils.get_robust_session()
    url = f"https://shipitalia.com/api/shipments?page=1&limit={limit}"

    try:
        response = session.get(
            url,
            headers={"x-api-key": config.SHIPITALIA_API_KEY, "Content-Type": "application/json"},
            timeout=30,
        )
        
        if response.status_code != 200:
            print(f"⚠️ Errore HTTP API: {response.status_code}")
            return []

        json_data = response.json()
        dati = json_data.get("data", [])

        # CASO 1: Lista diretta (raro, ma possibile)
        if isinstance(dati, list):
            return dati
        
        # CASO 2: Struttura a dizionario (Shipments + Pagination)
        # È quello che abbiamo scoperto grazie al tuo test!
        if isinstance(dati, dict):
            if "shipments" in dati:
                return dati["shipments"]
            # Fallback generico
            if "items" in dati:
                return dati["items"]

        return []

    except Exception as e:
        logger.log.errore(f"Errore recupero lista spedizioni: {e}")
        return []

def scarica_pdf(url_pdf, tracking):
    session = utils.get_robust_session()
    try:
        print(f"   ⬇️  Scaricamento etichetta in corso...")
        response = session.get(url_pdf, timeout=30)
        response.raise_for_status()
        
        os.makedirs("etichette", exist_ok=True)

        # 🔐 Sanitizzazione tracking per nome file
        safe_tracking = re.sub(r"[^A-Za-z0-9_-]", "_", tracking)

        nome_file = os.path.join("etichette", f"{safe_tracking}.pdf")

        with open(nome_file, "wb") as f:
            f.write(response.content)

            
        print(f"   💾 PDF Salvato: {nome_file}")
        logger.log.info(f"PDF salvato in: {nome_file}")
        
        try:
            webbrowser.open(os.path.abspath(nome_file))
        except: pass 
            
        return nome_file
    except Exception as e:
        logger.log.errore(f"Impossibile scaricare PDF da {url_pdf}: {e}")
        print(f"⚠️ Impossibile scaricare il PDF: {e}")
        return None

@logger.traccia
def genera_etichetta(payload_originale):
    session = utils.get_robust_session()
    
    # 1. Pulizia dati
    payload_clean = _prepara_payload_sicuro(payload_originale)
    
    try:
        # 2. Chiamata API
        response = session.post(
            config.API_URL_SHIPITALIA,
            json=payload_clean,
            headers={"x-api-key": config.SHIPITALIA_API_KEY, "Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        
        dati_risposta = result.get("data", {})
        tracking = dati_risposta.get("trackingCode")
        pdf_url = dati_risposta.get("labelUrl")
        
        if not tracking:
            raise ValueError("L'API non ha restituito un Tracking Code!")

        if pdf_url:
            scarica_pdf(pdf_url, tracking)
        
        return {
            "trackingCode": tracking,
            "labelUrl": pdf_url
        }

    except Exception as e:
        logger.log.errore(f"Errore API ShipItalia: {e}")
        logger.log.debug(f"Payload fallito: {payload_clean}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"🔍 Dettagli errore server: {e.response.text}")
        raise RuntimeError("Errore generazione etichetta") from e
