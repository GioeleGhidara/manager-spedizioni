# 📦 Spedizione Manager

Un tool gestionale in Python per automatizzare le spedizioni con **ShipItalia** e sincronizzare il tracking su **eBay**.

## ✨ Funzionalità Principali

* **Dashboard Ordini eBay:** Scarica automaticamente gli ordini "Da Spedire" e "In Viaggio" da eBay.
* **Cache Intelligente:** Salva i dati in memoria per una navigazione istantanea tra i menu.
* **Mittente Automatico:** Preleva l'indirizzo del mittente direttamente dal tuo account eBay (Registration Address).
* **Creazione Etichette:** Genera etichette di spedizione ShipItalia con un click, precompilando i dati del cliente.
* **Sync Automatico:** Carica automaticamente il codice di tracking su eBay e segna l'ordine come spedito.
* **Storico Interattivo:** Visualizza le ultime spedizioni create, controlla lo stato (Tracking) e permette di **riscaricare il PDF** in caso di smarrimento.
* **Logger Avanzato:** Registra tutte le operazioni, gli errori e le chiamate API in file di log giornalieri nella cartella `logs/`, mantenendo pulita la schermata.

---

## 📂 Struttura del Progetto

* **`main.py`**: Il cuore del programma. Gestisce il menu, la cache e il flusso.
* **`check_token.py`**: Modulo per verificare la validità e la data di scadenza del token eBay.
* **`ebay.py`**: Gestisce la comunicazione con eBay (scarico ordini, upload tracking, mittente).
* **`shipitalia.py`**: Gestisce le API di ShipItalia (etichette, storico, sanitizzazione).
* **`history.py`**: Gestisce il salvataggio e la lettura dello storico locale JSON.
* **`config.py`**: Centralizza la configurazione e le variabili d'ambiente.
* **`logger.py`**: Sistema di logging rotativo con decoratore `@traccia`.
* **`ui.py`**: Gestisce le stampe e l'interfaccia utente.
* **`utils.py`** & **`input_utils.py`**: Funzioni di supporto (peso, retry HTTP, input).

```bash
spedizioni shipitalia/
│
├── etichette/               # (Generata) Contiene i PDF scaricati
│
├── logs/                    # (Generata) Contiene i log giornalieri
│
├── .env                     # Password e API Key (SOLO IN LOCALE)
│
├── storico_spedizioni.json  # (Generata) Database locale spedizioni
│
├── main.py                  # Punto di ingresso e Menu principale
├── ebay.py                  # Logica API eBay (Ordini/Tracking/Mittente)
├── shipitalia.py            # Logica API ShipItalia (Etichette)
├── logger.py                # Sistema di tracciamento e rotazione log
├── config.py                # Validazione variabili d'ambiente
├── input_utils.py           # Gestione input utente e indirizzi
├── ui.py                    # Logica stampe e menu
└── utils.py                 # Funzioni tecniche (Peso, Sessioni HTTP)
```
---

## 🚀 Installazione e Configurazione

### 1. Requisiti
Assicurati di avere **Python** installato sul tuo computer.

### 2. Librerie
Installa le librerie necessarie eseguendo questo comando nel terminale:
```bash
pip install requests python-dotenv
```

### 3. File .env o Variabili di Sistema

**Metodo A: File .env (Standard):**

Crea un file chiamato **`.env`** nella cartella principale del progetto e inserisci le tue chiavi API:

```env
# --- OBBLIGATORI PER SPEDIRE ---
SHIPITALIA_API_KEY=tua_chiave_shipitalia
EBAY_XML_TOKEN=tuo_token_xml_ebay

# --- OPZIONALI (Per vedere i giorni alla scadenza Token) ---
EBAY_APP_ID=tuo_app_id
EBAY_DEV_ID=tuo_dev_id
EBAY_CERT_ID=tuo_cert_id
```
**Metodo B: Variabili di Sistema (Avanzato):**

Se preferisci non usare il file .env, puoi impostare le chiavi direttamente come Variabili d'Ambiente nel tuo sistema operativo (Windows/Linux/Mac). Le variabili richieste sono:

```env
# --- OBBLIGATORI PER SPEDIRE ---
SHIPITALIA_API_KEY=tua_chiave_shipitalia
EBAY_XML_TOKEN=tuo_token_xml_ebay

# --- OPZIONALI (Per vedere i giorni alla scadenza Token) ---
EBAY_APP_ID=tuo_app_id
EBAY_DEV_ID=tuo_dev_id
EBAY_CERT_ID=tuo_cert_id
```

*(Nota: Il token XML è fondamentale per le operazioni di scrittura su eBay)*

---

## 🎮 Come si usa

Avvia il programma dal terminale:

```bash
python main.py

```

### Il Menu Principale

1. **📋 Dashboard Ordini:**
* Visualizza una tabella con gli ordini eBay da spedire.
* Clicca su un ordine per spedirlo o su un ordine "In Viaggio" per vedere il tracking.


2. **📦 Spedisci da Lista (eBay):**
* Mostra la lista rapida degli ordini da evadere.
* Se non ce ne sono, permette l'inserimento manuale dell'Order ID.


3. **🚀 Etichetta rapida (No eBay):**
* Crea un'etichetta ShipItalia scollegata da eBay (utile per vendite private, Vinted, Subito, ecc.).
* L'indirizzo può essere inserito manualmente o incollato a blocchi.


4. **🔍 Storico ShipItalia (API):**
* Mostra la lista delle ultime etichette generate su ShipItalia.
* Permette di vedere i dettagli (peso, stato tracking).
* Permette di **riscaricare il PDF** dell'etichetta se non lo trovi più.

5. **📒 Storico Locale (Dettagliato):**
* Legge il file storico_spedizioni.json.
* Mantiene traccia di tutto ciò che hai spedito, inclusi i titoli degli oggetti.

---

## 📝 Log e Risoluzione Problemi

Il programma è progettato per non mostrare errori tecnici complessi a schermo.
Se qualcosa non funziona (es. un'etichetta non viene creata o eBay non si aggiorna):

1. Apri la cartella **`logs/`**.
2. Apri il file con la data di oggi (es. `log_2026-01-06.txt`).
3. Troverai il dettaglio esatto dell'errore (con orario e motivo).

*Nota: I log più vecchi di 30 giorni vengono cancellati automaticamente all'avvio del programma per risparmiare spazio.*

---

## ⚠️ Note Operative

* **Peso:** Va inserito in **kg** (es. `0.5` per 500g, `1.2` per 1.2kg). Il programma arrotonda automaticamente per eccesso step di 0.5kg come richiesto da ShipItalia.
* **Mittente:** Puoi modificare il file `config/mittente.txt` per impostare il tuo indirizzo predefinito e velocizzare le spedizioni.
