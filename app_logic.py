from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple


@dataclass
class CacheState:
    ordini: Optional[Dict[str, List[dict]]] = None
    last_update: Optional[datetime] = None


def set_cache(state: CacheState, da_spedire: List[dict], in_viaggio: List[dict]) -> None:
    state.ordini = {"da_spedire": da_spedire, "in_viaggio": in_viaggio}
    state.last_update = datetime.now()


def get_cached_lists(state: CacheState) -> Tuple[List[dict], List[dict]]:
    if not state.ordini:
        return [], []
    return state.ordini.get("da_spedire", []), state.ordini.get("in_viaggio", [])


def invalidate_cache(state: CacheState) -> None:
    state.ordini = None
    state.last_update = None


def resolve_dashboard_selection(da_spedire: List[dict], in_viaggio: List[dict], selection_index: int) -> dict:
    """
    Decodifica una selezione 1-based e ritorna un'azione.
    Azioni possibili: order, tracking, tracking_unavailable, invalid.
    """
    total = len(da_spedire) + len(in_viaggio)
    if selection_index < 1 or selection_index > total:
        return {"action": "invalid"}

    len_ds = len(da_spedire)
    if selection_index <= len_ds:
        ordine = da_spedire[selection_index - 1]
        return {"action": "order", "order": ordine}

    ordine = in_viaggio[selection_index - len_ds - 1]
    tracking = ordine.get("tracking")
    if tracking and tracking != "N.D.":
        return {"action": "tracking", "tracking": tracking}
    return {"action": "tracking_unavailable"}


def build_payload(
    weight: float,
    sender: dict,
    recipient: dict,
    discount_code: Optional[str] = None,
) -> dict:
    payload = {"weight": weight, "sender": sender, "recipient": recipient}
    if discount_code:
        payload["discountCode"] = discount_code
    return payload
