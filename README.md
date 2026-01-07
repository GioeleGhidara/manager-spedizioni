# 📦 Spedizione Manager

Un tool gestionale in Python per automatizzare le spedizioni con **ShipItalia** e sincronizzare il tracking su **eBay**.

## ✨ Funzionalità Principali

* **Dashboard Ordini eBay:** Scarica automaticamente gli ordini "Da Spedire" e "In Viaggio" da eBay.
* **Creazione Etichette:** Genera etichette di spedizione ShipItalia con un click, precompilando i dati del cliente.
* **Sync Automatico:** Carica automaticamente il codice di tracking su eBay e segna l'ordine come spedito.
* **Storico Interattivo:** Visualizza le ultime spedizioni create, controlla lo stato (Tracking) e permette di **riscaricare il PDF** in caso di smarrimento.
* **Logger Avanzato:** Registra tutte le operazioni, gli errori e le chiamate API in file di log giornalieri nella cartella `logs/`, mantenendo pulita la schermata.

---

## 📂 Struttura del Progetto

* **`main.py`**: Il cuore del programma. Gestisce il menu ciclico e il flusso delle operazioni.
* **`ebay.py`**: Gestisce la comunicazione con eBay (scarico ordini, upload tracking) utilizzando un parsing XML sicuro.
* **`shipitalia.py`**: Gestisce le API di ShipItalia (creazione etichetta, recupero storico, tracking).
* **`config.py`**: Gestisce la configurazione, le variabili d'ambiente e verifica la presenza delle chiavi.
* **`logger.py`**: Sistema di logging rotativo (elimina automaticamente i log più vecchi di 30 giorni) e decoratore `@traccia`.
* **`utils.py`** & **`input_utils.py`**: Funzioni di supporto per calcoli peso, parsing indirizzi e input utente.

```bash
spedizioni shipitalia/
│
├── config/                  # File di configurazione statica
│   └── mittente.txt         # Dati predefiniti del mittente
│
├── etichette/               # (Generata) Contiene i PDF scaricati
│
├── logs/                    # (Generata) Contiene i log giornalieri
│
├── .env                     # Password e API Key (SOLO IN LOCALE)
│
├── main.py                  # Punto di ingresso e Menu principale
├── ebay.py                  # Logica API eBay (Ordini/Tracking)
├── shipitalia.py            # Logica API ShipItalia (Etichette)
├── logger.py                # Sistema di tracciamento e rotazione log
├── config.py                # Validazione variabili d'ambiente
├── input_utils.py           # Gestione input utente e indirizzi
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
SHIPITALIA_API_KEY=tua_chiave_shipitalia
EBAY_XML_TOKEN=tuo_token_xml_ebay
```
**Metodo B: Variabili di Sistema (Avanzato):**

Se preferisci non usare il file .env, puoi impostare le chiavi direttamente come Variabili d'Ambiente nel tuo sistema operativo (Windows/Linux/Mac). Le variabili richieste sono:
```env
SHIPITALIA_API_KEY=tua_chiave_shipitalia
EBAY_XML_TOKEN=tuo_token_xml_ebay
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
* Digita il numero dell'ordine per avviare subito la creazione dell'etichetta.
* Visualizza anche gli ordini "In Viaggio" per monitoraggio.


2. **⌨️ Inserisci manualmente Order ID:**
* Utile se vuoi spedire un ordine eBay specifico di cui conosci già l'ID, saltando la dashboard.


3. **🚀 Etichetta rapida (No eBay):**
* Crea un'etichetta ShipItalia scollegata da eBay (utile per vendite private, Vinted, Subito, ecc.).
* L'indirizzo può essere inserito manualmente o incollato a blocchi.


4. **🔍 Storico Spedizioni & PDF:**
* Mostra la lista delle ultime etichette generate su ShipItalia.
* Permette di vedere i dettagli (peso, stato tracking).
* Permette di **riscaricare il PDF** dell'etichetta se non lo trovi più.

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
