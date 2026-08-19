# Telegram Bot Manager

Interfaccia grafica desktop per gestire un bot Telegram privato — avvia e ferma il bot, invia messaggi alla bacheca, gestisce gli utenti autorizzati, tutto senza toccare il codice.

![Screenshot](https://raw.githubusercontent.com/ELPythonEMI/ELtelegramBOTmanager/main/img.png)

---

## Funzionalità

- **Avvia / Ferma** il bot con un click, senza terminale
- **Bacheca messaggi** — testo e allegati (foto, GIF, documenti) con invio immediato o programmato per orario
- **Gestione utenti** — aggiungi, rimuovi e importa ID autorizzati salvati in `ids.json`
- **Token sicuro** — caricato da `config.json` esterno, mai hardcoded nel sorgente
- **Controllo accesso** — modalità solo autorizzati o aperto a tutti, cambiabile a runtime
- **Log integrato** — registro colorato con esportazione in `.txt`
- **Grafica dark** — UI professionale in stile dark, funziona su Windows, macOS e Linux

---

## Requisiti

- Python **3.10** o superiore
- pip

---

## Installazione

```bash
# 1. Clona il repository
git clone [https://github.com/tuo-utente/telegram-bot-manager](https://github.com/ELPythonEMI/ELtelegramBOTmanager).git
cd telegram-bot-manager

# 2. Installa la dipendenza
pip install python-telegram-bot --upgrade
```

---

## Configurazione

### 1. Token del bot

Al primo avvio viene creato automaticamente il file `config.json`:

```json
{
  "token": "INSERISCI_QUI_IL_TUO_TOKEN"
}
```

Puoi inserire il token direttamente in questo file oppure dalla tab **Impostazioni** dell'interfaccia grafica.

Per ottenere un token crea un bot tramite [@BotFather](https://t.me/BotFather) su Telegram.

### 2. Utenti autorizzati

Gli utenti sono salvati in `ids.json`:

```json
[
  { "id": 123456789, "label": "Mario" },
  { "id": 987654321, "label": "Luca" }
]
```

Puoi modificare la lista direttamente dalla tab **Utenti** nell'interfaccia.

---

## Utilizzo

```bash
python ELbotmanager.py
```

Oppure da VS Code: apri il file e premi `F5`.

### Struttura dei file

```
telegram-bot-manager/
├── ELbotmanager.py       # Applicazione principale
├── config.json           # Token bot (creato automaticamente)
├── ids.json              # Lista utenti autorizzati
├── accessi_el.csv        # Registro accessi (generato a runtime)
└── README.md
```

---

## Tab dell'interfaccia

| Tab | Descrizione |
|-----|-------------|
| **Bacheca** | Componi e invia messaggi con allegati e orario programmato |
| **Utenti** | Aggiungi, rimuovi e importa utenti autorizzati |
| **Impostazioni** | Gestisci il token, la modalità di accesso e i percorsi file |

---

## Parola chiave bot

Il bot risponde alla parola chiave `el` e al comando `/el`, inviando il contenuto configurato. Puoi modificare la parola chiave nel sorgente alla riga:

```python
PAROLA_CHIAVE = "el"
```

---

## Risoluzione problemi

**Import "telegram" non trovato in VS Code**

Il warning di Pylance compare quando il pacchetto non è installato nell'interprete selezionato da VS Code. Soluzione:

1. Apri il terminale integrato (`Ctrl+```)
2. Esegui `pip install python-telegram-bot --upgrade`
3. `Ctrl+Shift+P` → **Python: Select Interpreter** → scegli lo stesso Python
4. `Ctrl+Shift+P` → **Developer: Reload Window**

**Il bot non si avvia**

Verifica che il token in `config.json` sia corretto e che il bot non sia già in esecuzione su un altro processo.

---

## Licenza

MIT — libero per uso personale e commerciale.
