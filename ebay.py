import requests
import xml.etree.ElementTree as ET
from logger import log, traccia
from utils import normalizza_telefono, get_robust_session
from config import EBAY_XML_TOKEN

EBAY_XML_API_URL = "https://api.ebay.com/ws/api.dll"
EBAY_NS = {'ns': 'urn:ebay:apis:eBLBaseComponents'}

def _find_text(root, tag_name):
    element = root.find(f".//ns:{tag_name}", EBAY_NS)
    return element.text if element is not None else ""

def _format_data(iso_date):
    if not iso_date or len(iso_date) < 16: return "??"
    try:
        date_part = iso_date.split("T")[0]
        time_part = iso_date.split("T")[1][:5]
        dd, mm, yyyy = date_part.split("-")[2], date_part.split("-")[1], date_part.split("-")[0]
        return f"{dd}/{mm} {time_part}"
    except Exception:
        return iso_date

def _parse_indirizzo_xml(order_element):
    sa = order_element.find(".//ns:ShippingAddress", EBAY_NS)
    if sa is None: return None
    
    def get_sa_field(tag):
        el = sa.find(f"ns:{tag}", EBAY_NS)
        return el.text if el is not None else ""

    name = get_sa_field("Name")
    street1 = get_sa_field("Street1")
    street2 = get_sa_field("Street2")
    city = get_sa_field("CityName")
    zip_code = get_sa_field("PostalCode")
    phone_raw = get_sa_field("Phone")
    
    full_address = street1
    if street2: full_address += f" {street2}"
        
    return {
        "name": name,
        "address": full_address,
        "city": city,
        "postalCode": zip_code,
        "phone": normalizza_telefono(phone_raw)
    }

@traccia
def scarica_lista_ordini(giorni_storico=30):
    token = EBAY_XML_TOKEN
    if not token:
        log.errore("Token XML eBay mancante")
        print("⚠️ Manca token XML.")
        return [], []

    print(f"   ☁️  Scarico ordini eBay (Ultimi {giorni_storico} gg)...")

    xml_body = f"""<?xml version="1.0" encoding="utf-8"?>
<GetOrdersRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <RequesterCredentials><eBayAuthToken>{token}</eBayAuthToken></RequesterCredentials>
  <NumberOfDays>{giorni_storico}</NumberOfDays>
  <OrderRole>Seller</OrderRole>
  <DetailLevel>ReturnAll</DetailLevel>
</GetOrdersRequest>"""

    headers = {
        "X-EBAY-API-SITEID": "101",
        "X-EBAY-API-COMPATIBILITY-LEVEL": "1131",
        "X-EBAY-API-CALL-NAME": "GetOrders",
        "Content-Type": "text/xml"
    }

    da_spedire = []
    in_viaggio = []
    session = get_robust_session()

    try:
        response = session.post(EBAY_XML_API_URL, data=xml_body, headers=headers, timeout=30)
        response.raise_for_status()
        
        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as e:
            log.errore(f"XML non valido da eBay: {e}")
            return [], []

        ack = _find_text(root, "Ack")
        if ack == "Failure":
            error_msg = _find_text(root, "LongMessage")
            log.errore(f"Errore API eBay: {error_msg}")
            print(f"❌ Errore API eBay: {error_msg[:100]}...")
            return [], []

        orders = root.findall(".//ns:Order", EBAY_NS)
        
        for order in orders:
            order_id = _find_text(order, "OrderID")
            buyer = _find_text(order, "BuyerUserID")
            created_raw = _find_text(order, "CreatedTime")
            created_fmt = _format_data(created_raw)
            
            # --- BLOCCO SICUREZZA PAGAMENTI ---
            paid_time = _find_text(order, "PaidTime")
            shipped_time = _find_text(order, "ShippedTime")
            delivery_time = _find_text(order, "ActualDeliveryTime")
            
            # Se NON c'è PaidTime, l'utente non ha pagato -> SALTIAMO
            if not paid_time:
                log.info(f"Ordine {order_id} ignorato: NON ANCORA PAGATO.")
                continue 
            # ----------------------------------

            titolo = "Oggetto eBay"
            transaction = order.find(".//ns:Transaction", EBAY_NS)
            if transaction is not None:
                item = transaction.find("ns:Item", EBAY_NS)
                if item is not None:
                    t_val = item.find("ns:Title", EBAY_NS)
                    if t_val is not None: titolo = t_val.text

            titolo_corto = (titolo[:45] + '..') if len(titolo) > 45 else titolo
            destinatario = _parse_indirizzo_xml(order)
            
            if order_id and destinatario:
                obj_ordine = {
                    "order_id": order_id,
                    "buyer": buyer,
                    "date": created_fmt,
                    "title": titolo_corto,
                    "destinatario": destinatario
                }

                # Logica aggiornata:
                # 1. Deve essere PAGATO (già filtrato sopra)
                # 2. Se non ha ShippedTime -> DA SPEDIRE
                if not shipped_time:
                    da_spedire.append(obj_ordine)
                # 3. Se ha ShippedTime ma non DeliveryTime -> IN VIAGGIO
                elif not delivery_time:
                    in_viaggio.append(obj_ordine)

        log.info(f"Trovati {len(da_spedire)} da spedire (PAGATI) e {len(in_viaggio)} in viaggio.")
        return da_spedire, in_viaggio

    except Exception as e:
        log.errore(f"Errore durante scaricamento ordini: {e}")
        print(f"⚠️ Errore ricerca: {e}")
        return [], []

@traccia
def gestisci_ordine_ebay(order_id, tracking):
    try:
        invia_tracking_xml(order_id, tracking, "Poste Italiane")
        print("✅ Tracking caricato su eBay (XML).")
        log.successo(f"eBay aggiornato per {order_id} -> {tracking}")
    except Exception as e:
        log.errore(f"Fallimento aggiornamento eBay per {order_id}: {e}")
        print(f"⚠️ Errore aggiornamento eBay: {e}")

@traccia
def invia_tracking_xml(order_id, tracking, carrier):
    token = EBAY_XML_TOKEN
    if not token: raise RuntimeError("Manca EBAY_XML_TOKEN.")
    
    order_id_clean = order_id.strip().replace(" ", "")
    session = get_robust_session()
    
    xml_body = f"""<?xml version="1.0" encoding="utf-8"?>
<CompleteSaleRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <RequesterCredentials><eBayAuthToken>{token}</eBayAuthToken></RequesterCredentials>
  <OrderID>{order_id_clean}</OrderID>
  <Shipped>true</Shipped>
  <Shipment>
    <ShipmentTrackingDetails>
      <ShipmentTrackingNumber>{tracking}</ShipmentTrackingNumber>
      <ShippingCarrierUsed>{carrier}</ShippingCarrierUsed>
    </ShipmentTrackingDetails>
  </Shipment>
</CompleteSaleRequest>"""
    
    headers = {
        "X-EBAY-API-SITEID": "101",
        "X-EBAY-API-COMPATIBILITY-LEVEL": "1131",
        "X-EBAY-API-CALL-NAME": "CompleteSale",
        "Content-Type": "text/xml",
    }
    
    print(f"   ☁️  Invio tracking a eBay ({order_id_clean})...")
    response = session.post(EBAY_XML_API_URL, data=xml_body, headers=headers, timeout=30)
    response.raise_for_status()
    
    try:
        root = ET.fromstring(response.content)
        ack = _find_text(root, "Ack")
        if ack == "Failure":
            err = _find_text(root, "LongMessage") or _find_text(root, "ShortMessage")
            raise ValueError(f"eBay ha risposto Failure: {err}" if err else "eBay ha risposto Failure")
    except ET.ParseError:
        if response.status_code >= 400:
            raise ValueError(f"Risposta eBay non valida (HTTP {response.status_code})")

    return True