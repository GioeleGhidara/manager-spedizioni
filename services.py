import app_logic


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

    def invalida_cache(self):
        app_logic.invalidate_cache(self.cache_state)

    def resolve_dashboard(self, da_spedire, in_viaggio, selection_index):
        return app_logic.resolve_dashboard_selection(da_spedire, in_viaggio, selection_index)

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
