import xml.etree.ElementTree as ET
from datetime import datetime
import config
import logger
import utils

@logger.traccia
def check_scadenza_token_silenzioso():
    """
    Controlla la scadenza del token all'avvio.
    Ritorna una stringa di avviso se manca poco, altrimenti None.
    """
    # Se mancano le chiavi nel .env, saltiamo il controllo senza errori
    if not all([config.EBAY_APP_ID, config.EBAY_DEV_ID, config.EBAY_CERT_ID, config.EBAY_XML_TOKEN]):
        return None

    # Usiamo il namespace dinamico anche nell'XML (opzionale, ma coerente)
    ns_url = config.EBAY_NS['ns']
    xml_body = f"""<?xml version="1.0" encoding="utf-8"?>
    <GetTokenStatusRequest xmlns="{ns_url}">
      <RequesterCredentials><eBayAuthToken>{config.EBAY_XML_TOKEN}</eBayAuthToken></RequesterCredentials>
    </GetTokenStatusRequest>"""

    headers = {
        "X-EBAY-API-SITEID": "101",
        "X-EBAY-API-COMPATIBILITY-LEVEL": "1131",
        "X-EBAY-API-CALL-NAME": "GetTokenStatus",
        "X-EBAY-API-APP-NAME": config.EBAY_APP_ID,
        "X-EBAY-API-DEV-NAME": config.EBAY_DEV_ID,
        "X-EBAY-API-CERT-NAME": config.EBAY_CERT_ID,
        "Content-Type": "text/xml"
    }

    try:
        session = utils.get_robust_session()
        # QUI: Usiamo la costante EBAY_XML_API_URL invece dell'URL scritto a mano
        response = session.post(config.EBAY_XML_API_URL, data=xml_body, headers=headers, timeout=5)
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            
            # QUI: Usiamo EBAY_NS importato invece di ridefinire {'ns': ...}
            nodi_data = [
                root.find(".//ns:HardExpirationTime", config.EBAY_NS),
                root.find(".//ns:ExpirationTime", config.EBAY_NS)
            ]
            
            data_str = next((n.text for n in nodi_data if n is not None), None)

            if data_str:
                raw_date = data_str.replace("Z", "").split(".")[0]
                scadenza = datetime.strptime(raw_date, "%Y-%m-%dT%H:%M:%S")
                delta = scadenza - datetime.now()
                giorni = delta.days

                if giorni < 0:
                    return f"❌ IL TOKEN EBAY È SCADUTO DA {abs(giorni)} GIORNI! Rigeneralo subito."
                elif giorni < 60:
                    return f"⚠️  ATTENZIONE: Il token eBay scade tra {giorni} giorni ({scadenza.strftime('%d/%m/%Y')})."
                
                logger.log.info(f"Check Token OK: scade tra {giorni} gg.")
                return None

    except Exception as e:
        logger.log.warning(f"Check token avvio fallito (ignorato): {e}")
        return None
        
    return None
