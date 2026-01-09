import xml.etree.ElementTree as ET
from datetime import datetime
from utils import get_robust_session
from logger import log, traccia
from config import (
    EBAY_XML_TOKEN, EBAY_APP_ID, EBAY_DEV_ID, EBAY_CERT_ID,
    EBAY_XML_API_URL, EBAY_NS,
    EBAY_SITE_ID, EBAY_COMPATIBILITY_LEVEL,
)

@traccia
def check_scadenza_token_silenzioso():
    """
    Controlla la scadenza del token all'avvio.
    Ritorna una stringa di avviso se manca poco, altrimenti None.
    """
    # Se mancano le chiavi nel .env, saltiamo il controllo senza errori
    if not all([EBAY_APP_ID, EBAY_DEV_ID, EBAY_CERT_ID, EBAY_XML_TOKEN]):
        return None

    # Usiamo il namespace dinamico anche nell'XML (opzionale, ma coerente)
    ns_url = EBAY_NS['ns']
    xml_body = f"""<?xml version="1.0" encoding="utf-8"?>
    <GetTokenStatusRequest xmlns="{ns_url}">
      <RequesterCredentials><eBayAuthToken>{EBAY_XML_TOKEN}</eBayAuthToken></RequesterCredentials>
    </GetTokenStatusRequest>"""

    headers = {
        "X-EBAY-API-SITEID": EBAY_SITE_ID,
        "X-EBAY-API-COMPATIBILITY-LEVEL": EBAY_COMPATIBILITY_LEVEL,
        "X-EBAY-API-CALL-NAME": "GetTokenStatus",
        "X-EBAY-API-APP-NAME": EBAY_APP_ID,
        "X-EBAY-API-DEV-NAME": EBAY_DEV_ID,
        "X-EBAY-API-CERT-NAME": EBAY_CERT_ID,
        "Content-Type": "text/xml"
    }

    try:
        session = get_robust_session()
        response = session.post(EBAY_XML_API_URL, data=xml_body, headers=headers, timeout=5)

        if response.status_code == 200:
            root = ET.fromstring(response.content)

            nodi_data = [
                root.find(".//ns:HardExpirationTime", EBAY_NS),
                root.find(".//ns:ExpirationTime", EBAY_NS)
            ]

            data_str = next((n.text for n in nodi_data if n is not None), None)

            if data_str:
                raw_date = data_str.replace("Z", "").split(".")[0]
                scadenza = datetime.strptime(raw_date, "%Y-%m-%dT%H:%M:%S")
                delta = scadenza - datetime.now()
                giorni = delta.days

                if giorni < 0:
                    return f"ERROR: TOKEN EBAY SCADUTO DA {abs(giorni)} GIORNI. Rigeneralo subito."
                elif giorni < 60:
                    return f"WARN: Il token eBay scade tra {giorni} giorni ({scadenza.strftime('%d/%m/%Y')})."

                log.info(f"Check Token OK: scade tra {giorni} gg.")
                return None

    except Exception as e:
        log.warning(f"Check token avvio fallito (ignorato): {e}")
        return None

    return None
