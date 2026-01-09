# Spedizione Manager

Un tool gestionale in Python per automatizzare le spedizioni con ShipItalia e sincronizzare il tracking su eBay.

## Funzionalita Principali

- Dashboard ordini eBay: scarica automaticamente gli ordini "Da Spedire" e "In Viaggio".
- Cache intelligente: salva i dati in memoria per una navigazione rapida tra i menu.
- Mittente automatico: preleva l'indirizzo del mittente direttamente dal tuo account eBay (Registration Address).
- Creazione etichette: genera etichette di spedizione ShipItalia con un click, precompilando i dati del cliente.
- Sync automatico: carica il codice di tracking su eBay e segna l'ordine come spedito.
- Storico interattivo: visualizza le ultime spedizioni create, controlla lo stato (tracking) e permette di riscaricare il PDF.
- Logger avanzato: registra tutte le operazioni, gli errori e le chiamate API in file di log giornalieri nella cartella `logs/`.

---

## Struttura del Progetto

- `main.py`: il cuore del programma. Gestisce il menu, la cache e il flusso.
- `check_token.py`: verifica la validita e la data di scadenza del token eBay.
- `ebay.py`: comunicazione con eBay (scarico ordini, upload tracking, mittente).
- `shipitalia.py`: comunicazione con ShipItalia (etichette, storico, sanitizzazione).
- `history.py`: salvataggio e lettura dello storico locale JSON.
- `config.py`: configurazione e variabili d'ambiente.
- `logger.py`: sistema di logging rotativo con decoratore `@traccia`.
- `ui.py`: stampe e interfaccia utente.
- `utils.py` e `input_utils.py`: funzioni di supporto (peso, retry HTTP, input).

```bash
spedizioni shipitalia/
|-- etichette/               # (Generata) Contiene i PDF scaricati
|-- logs/                    # (Generata) Contiene i log giornalieri
|-- .env                     # Password e API Key (SOLO IN LOCALE)
|-- storico_spedizioni.json  # (Generata) Database locale spedizioni
|-- main.py                  # Punto di ingresso e menu principale
|-- ebay.py                  # Logica API eBay (ordini/tracking/mittente)
|-- shipitalia.py            # Logica API ShipItalia (etichette)
|-- logger.py                # Sistema di tracciamento e rotazione log
|-- config.py                # Validazione variabili d'ambiente
|-- input_utils.py           # Gestione input utente e indirizzi
|-- ui.py                    # Logica stampe e menu
|-- utils.py                 # Funzioni tecniche (peso, sessioni HTTP)
```

---

## Installazione e Configurazione

### 1. Requisiti
Assicurati di avere Python installato sul tuo computer.

### 2. Librerie
Installa le librerie necessarie eseguendo questo comando nel terminale:
```bash
pip install requests python-dotenv
```

### 3. File .env o Variabili di Sistema

Metodo A: file .env

Crea un file chiamato `.env` nella cartella principale del progetto e inserisci le tue chiavi API:

```env
# --- OBBLIGATORI PER SPEDIRE ---
SHIPITALIA_API_KEY=tua_chiave_shipitalia
EBAY_XML_TOKEN=tuo_token_xml_ebay

# --- OPZIONALI (Per vedere i giorni alla scadenza Token) ---
EBAY_APP_ID=tuo_app_id
EBAY_DEV_ID=tuo_dev_id
EBAY_CERT_ID=tuo_cert_id
```

Metodo B: variabili di sistema

Se preferisci non usare il file .env, puoi impostare le chiavi direttamente come variabili d'ambiente nel tuo sistema operativo. Le variabili richieste sono:

```env
# --- OBBLIGATORI PER SPEDIRE ---
SHIPITALIA_API_KEY=tua_chiave_shipitalia
EBAY_XML_TOKEN=tuo_token_xml_ebay

# --- OPZIONALI (Per vedere i giorni alla scadenza Token) ---
EBAY_APP_ID=tuo_app_id
EBAY_DEV_ID=tuo_dev_id
EBAY_CERT_ID=tuo_cert_id
```

Nota: il token XML e fondamentale per le operazioni di scrittura su eBay.

---

## Come si usa

Avvia il programma dal terminale:

```bash
python main.py
```

### Menu Principale

1. Dashboard ordini
   - Visualizza una tabella con gli ordini eBay da spedire.
   - Seleziona un ordine per spedirlo o un ordine "In Viaggio" per vedere il tracking.

2. Spedisci da lista (eBay)
   - Mostra la lista rapida degli ordini da evadere.
   - Se non ce ne sono, permette l'inserimento manuale dell'Order ID.

3. Etichetta rapida (no eBay)
   - Crea un'etichetta ShipItalia scollegata da eBay (utile per vendite private, Vinted, Subito, ecc.).
   - L'indirizzo puo essere inserito manualmente o incollato a blocchi.

4. Storico ShipItalia (API)
   - Mostra la lista delle ultime etichette generate su ShipItalia.
   - Permette di vedere i dettagli (peso, stato tracking).
   - Permette di riscaricare il PDF dell'etichetta se non lo trovi piu.

5. Storico locale (dettagliato)
   - Legge il file `storico_spedizioni.json`.
   - Mantiene traccia di tutto cio che hai spedito, inclusi i titoli degli oggetti.

---

## Log e risoluzione problemi

Il programma e progettato per non mostrare errori tecnici complessi a schermo.
Se qualcosa non funziona (es. un'etichetta non viene creata o eBay non si aggiorna):

1. Apri la cartella `logs/`.
2. Apri il file con la data di oggi (es. `log_2026-01-06.txt`).
3. Troverai il dettaglio esatto dell'errore (con orario e motivo).

Nota: i log piu vecchi di 30 giorni vengono cancellati automaticamente all'avvio del programma.

---

## Note operative

- Peso: va inserito in kg (es. `0.5` per 500g, `1.2` per 1.2kg). Il programma arrotonda automaticamente per eccesso step di 0.5kg come richiesto da ShipItalia.
- Mittente: puoi modificare il file `config/mittente.txt` per impostare il tuo indirizzo predefinito e velocizzare le spedizioni.
