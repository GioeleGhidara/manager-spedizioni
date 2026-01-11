from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple


@dataclass
class CacheState:
    ordini: Optional[Dict[str, List[dict]]] = None
    last_update: Optional[datetime] = None


@dataclass
class ListCacheState:
    items: Optional[List[dict]] = None
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


def set_list_cache(state: ListCacheState, items: List[dict]) -> None:
    state.items = items
    state.last_update = datetime.now()


def get_cached_list(state: ListCacheState) -> List[dict]:
    return state.items or []


def invalidate_list_cache(state: ListCacheState) -> None:
    state.items = None
    state.last_update = None


def resolve_dashboard_selection(ordini: List[dict], selection_index: int) -> dict:
    """
    Decodifica una selezione 1-based e ritorna un'azione.
    Azioni possibili: order, tracking, tracking_unavailable, invalid.
    """
    total = len(ordini)
    if selection_index < 1 or selection_index > total:
        return {"action": "invalid"}

    ordine = ordini[selection_index - 1]
    stato = ordine.get("dashboard_status", "")
    tracking = ordine.get("tracking")

    if stato == "DA SPEDIRE":
        return {"action": "order", "order": ordine}

    if tracking and tracking != "N.D.":
        # MODIFICA APPLICATA QUI SOTTO:
        return {"action": "tracking", "tracking": tracking, "status": stato}

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