import requests
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from datetime import datetime
from logger import log, traccia
from utils import normalizza_telefono, get_robust_session
from config import EBAY_XML_TOKEN, EBAY_XML_API_URL, EBAY_NS

def _find_text(root, tag_name):
    if root is None: return ""
    element = root.find(f".//ns:{tag_name}", EBAY_NS)
    return element.text if element is not None else ""

def _format_data(iso_date):
    if not iso_date: return "??"
    try:
        clean_date = iso_date.replace("Z", "+00:00")
        if "." in clean_date:
            main_part, frac = clean_date.split(".")
            frac = frac[:6]
            clean_date = f"{main_part}.{frac}"
        dt = datetime.fromisoformat(clean_date)
        return dt.strftime("%d/%m %H:%M")
    except ValueError:
        return iso_date

# --- NUOVA FUNZIONE HELPER (Riutilizzabile) ---
def _parse_nodo_indirizzo(addr_node):
    """Parsa un nodo AddressType (usato sia per ShippingAddress che per RegistrationAddress)."""
    if addr_node is None: return None
    
    def get_field(tag):
        el = addr_node.find(f"ns:{tag}", EBAY_NS)
        return el.text if el is not None else ""

    name = get_field("Name")
    street1 = get_field("Street1")
    street2 = get_field("Street2")
    city = get_field("CityName")
    zip_code = get_field("PostalCode")
    phone_raw = get_field("Phone")
    
    full_address = street1
    if street2: full_address += f" {street2}"
        
    return {
        "name": name,
        "address": full_address,
        "city": city,
        "postalCode": zip_code,
        "phone": normalizza_telefono(phone_raw)
    }

def _parse_indirizzo_xml(order_element):
    """Wrapper per compatibilità con la logica esistente degli ordini."""
    sa = order_element.find(".//ns:ShippingAddress", EBAY_NS)
    return _parse_nodo_indirizzo(sa)

# --- NUOVA FUNZIONE: RECUPERO MITTENTE ---
@traccia
def get_mittente_ebay():
    """Scarica l'indirizzo di registrazione dell'account eBay (Mittente)."""
    token = EBAY_XML_TOKEN
    if not token: return None
    
    print("   ☁️  Recupero indirizzo mittente da eBay...")

    xml_body = f"""<?xml version="1.0" encoding="utf-8"?>
<GetUserRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <RequesterCredentials><eBayAuthToken>{token}</eBayAuthToken></RequesterCredentials>
  <DetailLevel>ReturnAll</DetailLevel>
</GetUserRequest>"""

    headers = {
        "X-EBAY-API-SITEID": "101",
        "X-EBAY-API-COMPATIBILITY-LEVEL": "1131",
        "X-EBAY-API-CALL-NAME": "GetUser",
        "Content-Type": "text/xml"
    }

    session = get_robust_session()

    try:
        response = session.post(EBAY_XML_API_URL, data=xml_body, headers=headers, timeout=30)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        
        # Check Errori
        ack = _find_text(root, "Ack")
        if ack == "Failure":
            log.errore("Errore GetUser (Mittente)")
            return None

        # Cerca l'indirizzo di registrazione dell'utente
        reg_addr = root.find(".//ns:User/ns:RegistrationAddress", EBAY_NS)
        if reg_addr is not None:
            return _parse_nodo_indirizzo(reg_addr)
            
    except Exception as e:
        log.errore(f"Errore recupero mittente eBay: {e}")
        return None
    
    return None

@traccia
def scarica_lista_ordini(giorni_storico=30):
    da_spedire = []
    in_viaggio = []

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

        orders = root.findall(".//ns:Order", EBAY_NS) or []
        
        for order in orders:
            order_id = _find_text(order, "OrderID")
            status = _find_text(order, "OrderStatus")
            
            if status in ["Cancelled", "Inactive"]:
                continue

            paid_time = _find_text(order, "PaidTime")
            if not paid_time:
                continue 

            shipped_time = _find_text(order, "ShippedTime")
            delivery_time = _find_text(order, "ActualDeliveryTime")
            
            created_fmt = _format_data(_find_text(order, "CreatedTime"))
            shipped_fmt = _format_data(shipped_time) if shipped_time else "-"
            delivered_fmt = _format_data(delivery_time) if delivery_time else "-"

            # --- ESTRAZIONE TRACKING UNIVERSALE ---
            tracking_code = "N.D."
            track_nodes = order.findall(".//ns:ShipmentTrackingNumber", EBAY_NS)
            if track_nodes:
                for node in track_nodes:
                    if node.text and len(node.text.strip()) > 5:
                        tracking_code = node.text.strip()
                        break
            # --------------------------------------

            titolo = "Oggetto eBay"
            try:
                t_node = order.find(".//ns:Item/ns:Title", EBAY_NS)
                if t_node is not None: titolo = t_node.text
            except: pass

            titolo_corto = (titolo[:40] + '..') if len(titolo) > 40 else titolo
            destinatario = _parse_indirizzo_xml(order)
            
            if order_id and destinatario:
                obj_ordine = {
                    "order_id": order_id,
                    "buyer": _find_text(order, "BuyerUserID"),
                    "date": created_fmt,
                    "title": titolo_corto,
                    "destinatario": destinatario,
                    "shipped_at": shipped_fmt,
                    "delivered_at": delivered_fmt,
                    "amount": _find_text(order, "AmountPaid"),
                    "tracking": tracking_code 
                }

                if not shipped_time:
                    obj_ordine["status_interno"] = "DA_SPEDIRE"
                    da_spedire.append(obj_ordine)
                elif not delivery_time:
                    obj_ordine["status_interno"] = "IN_VIAGGIO"
                    in_viaggio.append(obj_ordine)

        log.info(f"Trovati {len(da_spedire)} da spedire (PAGATI) e {len(in_viaggio)} in viaggio.")
        return da_spedire, in_viaggio

    except Exception as e:
        log.errore(f"Errore durante scaricamento ordini: {e}")
        print(f"⚠️ Errore ricerca: {e}")
        return [], []

@traccia
def gestisci_ordine_ebay(order_id, tracking):
    carrier = "Poste Italiane" 
    try:
        invia_tracking_xml(order_id, tracking, carrier)
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
    
    tracking_safe = escape(tracking)
    carrier_safe = escape(carrier)
    
    xml_body = f"""<?xml version="1.0" encoding="utf-8"?>
<CompleteSaleRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <RequesterCredentials><eBayAuthToken>{token}</eBayAuthToken></RequesterCredentials>
  <OrderID>{order_id_clean}</OrderID>
  <Shipped>true</Shipped>
  <Shipment>
    <ShipmentTrackingDetails>
      <ShipmentTrackingNumber>{tracking_safe}</ShipmentTrackingNumber>
      <ShippingCarrierUsed>{carrier_safe}</ShippingCarrierUsed>
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
            err_long = _find_text(root, "LongMessage")
            err_short = _find_text(root, "ShortMessage")
            full_err = f"{err_short} - {err_long}".strip(" -")
            raise ValueError(f"eBay Failure: {full_err}")
            
    except ET.ParseError:
        if response.status_code >= 400:
            raise ValueError(f"Risposta eBay non valida (HTTP {response.status_code})")

    return True