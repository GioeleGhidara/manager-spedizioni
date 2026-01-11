import app_logic
import config
import utils
from concurrent.futures import ThreadPoolExecutor, as_completed


class SpedizioniService:
    def __init__(self, ebay_mod, ship_mod, history_mod):
        self.ebay = ebay_mod
        self.ship = ship_mod
        self.history = history_mod
        self.cache_state = app_logic.CacheState()
        self.ship_cache_state = app_logic.ListCacheState()

    def carica_ordini(self, giorni=30):
        return self.ebay.scarica_lista_ordini(giorni)

    def get_cache_last_update(self):
        return self.cache_state.last_update

    def carica_ordini_cached(self, giorni=30):
        if self.cache_state.ordini is None:
            da_spedire, in_viaggio = self.ebay.scarica_lista_ordini(giorni)
            app_logic.set_cache(self.cache_state, da_spedire, in_viaggio)
        return app_logic.get_cached_lists(self.cache_state)

    def _classifica_tracking_poste(self, tracking):
        if not tracking or tracking == "N.D.":
            return "DA SPEDIRE", ""
        dati = utils.get_stato_tracking_poste_cached(tracking)
        if not dati:
            return "ETICHETTA CREATA", ""
        msg = utils.estrai_messaggio_poste(dati)
        if msg and "tracciatura non disponibile" in msg.lower():
            return "ETICHETTA CREATA", ""
        if isinstance(dati, dict):
            if dati.get("esitoRicerca") == "2" and not dati.get("listaMovimenti"):
                return "ETICHETTA CREATA", ""
        stato_testo = utils.estrai_stato_poste(dati).lower()
        if "consegn" in stato_testo:
            posizione = utils.estrai_posizione_poste(dati)
            return "CONSEGNATO", posizione
        if isinstance(dati, dict) and dati.get("listaMovimenti") == []:
            return "ETICHETTA CREATA", ""
        if isinstance(dati, list) and len(dati) == 0:
            return "ETICHETTA CREATA", ""
        posizione = utils.estrai_posizione_poste(dati)
        return "IN TRANSITO", posizione

    def prepara_dashboard_poste(self, giorni=30):
        da_spedire, in_viaggio = self.carica_ordini_cached(giorni)
        ordini = da_spedire + in_viaggio
        trackings = []
        for ordine in ordini:
            tracking = ordine.get("tracking")
            if tracking and tracking != "N.D.":
                trackings.append(tracking)

        stato_tracking = {}
        if trackings:
            max_workers = max(1, min(len(set(trackings)), config.TRACKING_MAX_WORKERS))
            if max_workers > 1:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_map = {executor.submit(self._classifica_tracking_poste, t): t for t in set(trackings)}
                    for future in as_completed(future_map):
                        t = future_map[future]
                        try:
                            stato_tracking[t] = future.result()
                        except Exception:
                            stato_tracking[t] = ("ETICHETTA CREATA", "")
            else:
                t = trackings[0]
                stato_tracking[t] = self._classifica_tracking_poste(t)
        stato_precedente = self.history.leggi_stato_dashboard()
        cambiamenti = []
        stato_corrente = {}
        dashboard = []
        for ordine in ordini:
            order_id = ordine.get("order_id")
            tracking = ordine.get("tracking")
            if tracking and tracking != "N.D.":
                stato, posizione = stato_tracking.get(tracking, ("ETICHETTA CREATA", ""))
            else:
                stato, posizione = self._classifica_tracking_poste(tracking)
            if order_id:
                stato_corrente[order_id] = {
                    "status": stato,
                    "tracking": tracking,
                }
                prev = stato_precedente.get(order_id)
                prev_status = prev.get("status") if isinstance(prev, dict) else prev
                if prev_status and prev_status != stato:
                    cambiamenti.append({
                        "order_id": order_id,
                        "buyer": ordine.get("buyer", ""),
                        "title": ordine.get("title", ""),
                        "from_status": prev_status,
                        "to_status": stato,
                    })
            item = dict(ordine)
            item["dashboard_status"] = stato
            item["dashboard_posizione"] = posizione
            if stato != "CONSEGNATO":
                dashboard.append(item)
        self.history.salva_stato_dashboard(stato_corrente)
        ordine_stati = ["DA SPEDIRE", "ETICHETTA CREATA", "IN TRANSITO"]
        ordinati = []
        for stato in ordine_stati:
            ordinati.extend([item for item in dashboard if item.get("dashboard_status") == stato])
        return ordinati, cambiamenti

    def invalida_cache(self):
        app_logic.invalidate_cache(self.cache_state)

    def resolve_dashboard(self, ordini, selection_index):
        return app_logic.resolve_dashboard_selection(ordini, selection_index)

    def resolve_lista_spedire(self, da_spedire, selection_index):
        if selection_index < 1 or selection_index > len(da_spedire):
            return {"action": "invalid"}
        ordine = da_spedire[selection_index - 1]
        return {"action": "order", "order": ordine}

    def resolve_storico_index(self, lista, selection_index):
        idx = selection_index - 1
        if 0 <= idx < len(lista):
            return {"action": "item", "index": idx, "item": lista[idx]}
        return {"action": "invalid"}

    def crea_etichetta(self, payload):
        return self.ship.genera_etichetta(payload)

    def lista_spedizioni(self, limit=15):
        return self.ship.get_lista_spedizioni(limit=limit)

    def get_ship_cache_last_update(self):
        return self.ship_cache_state.last_update

    def lista_spedizioni_cached(self, limit=15):
        if self.ship_cache_state.items is None:
            lista = self.ship.get_lista_spedizioni(limit=limit)
            app_logic.set_list_cache(self.ship_cache_state, lista)
        return app_logic.get_cached_list(self.ship_cache_state)

    def invalida_ship_cache(self):
        app_logic.invalidate_list_cache(self.ship_cache_state)

    def aggiorna_tracking_ebay(self, order_id, tracking):
        self.ebay.gestisci_ordine_ebay(order_id, tracking)

    def salva_storico(self, **kwargs):
        return self.history.salva_in_storico(**kwargs)
