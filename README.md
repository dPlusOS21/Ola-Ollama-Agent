# Ollama Agent

Un assistente di coding AI per il terminale, ispirato a Claude Code.
Utilizza **Ollama** come provider predefinito, con la doppia possibilità di usare **modelli cloud** (eseguiti su infrastruttura Ollama) o **modelli locali** (eseguiti sulla tua macchina). Supporta anche altri provider compatibili OpenAI (OpenAI, Groq, OpenRouter).

```
┌──────────────────────────────────────────────────────────────┐
│   ┌────────┐                                                  │
│   │ ◉    ◉ │   Ollama Agent  v0.6.0 — AI coding assistant    │
│   │  ────  │   ─────────────────────────────────────────     │
│   └───┬────┘   Type / for commands                           │
│  ┌────┴─────┐  Ctrl+C cancel  ·  Ctrl+D exit                 │
│  │  O·L·A   │                                                 │
│  └──────────┘                                                 │
  provider: ollama | model: deepseek-v3.1:671b-cloud

> aggiungi il type hint a main

  read_file(path='main.py')
  ✓  1    import sys...

  edit_file(path='main.py', old_string='def main():', new_string='def main() -> None:')
  ╭── Diff preview ──╮
  │  - def main():   │
  │  + def main() -> None: │
  ╰──────────────────╯
  Execute? [Y/n/auto] Y
  ✓  Successfully edited main.py

 deepseek-v3.1:671b-cloud  │  session: 1.2k tok  (950 in / 270 out)  │  weekly: 12.4k tok
```

---

## Requisiti

- Python 3.10+
- [Ollama](https://ollama.com) — se non è installato, lo script di installazione lo installa automaticamente

---

## Installazione

### Metodo rapido (consigliato)

Clona o scarica la cartella del progetto, poi:

```bash
# Linux / macOS
bash install.sh

# Windows
install.bat   ← doppio click
```

Lo script di installazione gestisce tutto automaticamente:

1. **Verifica Python 3.10+** e pip
2. **Ollama non installato?** → propone di installarlo automaticamente (default: sì)
3. **Ollama già installato?** → controlla se esiste una versione più recente su GitHub e chiede all'utente se vuole aggiornare (default: no)
4. **Installa Ollama Agent** e il comando `ola`
5. **Crea il file `.env`** dal template (se non esiste)

> **Nota:** l'installazione e l'aggiornamento di Ollama sono sempre **a scelta dell'utente** — lo script chiede conferma prima di procedere. Ollama Agent può funzionare anche senza Ollama se si usa un provider alternativo (OpenAI, Groq, OpenRouter).

### Manuale dalla cartella sorgente

```bash
pip install .
```

### Solo il file wheel (senza sorgenti)

Copia `dist/ollama_agent-0.6.0-py3-none-any.whl` sul PC di destinazione, poi:

```bash
pip install ollama_agent-0.6.0-py3-none-any.whl
```

### Da GitHub (se pubblicato)

```bash
pip install git+https://github.com/utente/ollama-agent.git
```

Dopo l'installazione il comando `ola` è disponibile ovunque nel terminale.

---

## Installazione su PC senza privilegi di amministratore

Se sei un **utente semplice** su un PC (scuola, ufficio, PC condiviso) dove non hai i permessi di admin/sudo, ola può comunque essere installato — con alcune differenze tra Linux e Windows.

### Linux senza `sudo`

| Componente | Installabile da utente? | Come |
|---|---|---|
| **Python 3.10+** | ✅ Sì (se non c'è già) | Via [**pyenv**](https://github.com/pyenv/pyenv) o **miniconda** installati nella tua home |
| **ola** | ✅ Sì | `pip install --user .` → va in `~/.local/bin/` |
| **Dipendenze Python** (openai, rich, mcp, ecc.) | ✅ Sì | `pip install --user` le installa in `~/.local/` |
| **Ollama** | ❌ No | L'installer ufficiale richiede `sudo` |
| **libportaudio2** (per `/voice`) | ❌ No | Richiede `sudo apt install` — `/voice` non sarà disponibile |
| **Node.js** (per MCP via `npx`) | ✅ Sì | Installabile via **nvm** nella tua home senza `sudo` |

**Procedura Linux senza sudo:**

```bash
# 1. Se non hai Python 3.10+, installa pyenv
curl https://pyenv.run | bash
pyenv install 3.11
pyenv global 3.11

# 2. Installa ola
cd /percorso/ollama-agent
pip install --user .

# 3. Aggiungi ~/.local/bin al PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 4. Configura un provider cloud (Groq ha tier gratuito generoso)
export GROQ_API_KEY=gsk_...
ola -p groq
```

### Windows senza privilegi di admin

Su Windows la situazione è spesso **più favorevole** di Linux: molti installer hanno l'opzione "per utente corrente" che non richiede admin.

| Componente | Installabile da utente? | Come |
|---|---|---|
| **Python 3.10+** | ✅ Sì | Installer ufficiale da [python.org](https://www.python.org/downloads/) — spunta "Add Python to PATH", si installa in `%LOCALAPPDATA%\Programs\Python\` |
| **ola** | ✅ Sì | `pip install --user .` → va in `%APPDATA%\Python\Python3XX\Scripts\` |
| **Dipendenze Python** | ✅ Sì | `pip install --user` |
| **Ollama** | ⚠️ Dipende | `OllamaSetup.exe` recenti installano in `%LOCALAPPDATA%\Programs\Ollama\` **senza admin**; versioni vecchie richiedevano admin |
| **libportaudio per `/voice`** | ✅ Sì, automatico | Su Windows `pip install sounddevice` include le DLL precompilate — **nessuna dipendenza di sistema richiesta** |
| **Node.js** (per MCP) | ✅ Sì | Installer ufficiale con "Install just for me", oppure **nvm-windows** / **fnm** |

**La buona notizia su Windows:** a differenza di Linux, il comando `/voice` funziona anche senza admin, perché il pacchetto `sounddevice` include già tutto il necessario.

**Procedura Windows senza admin:**

```cmd
:: 1. Scarica Python 3.10+ da python.org, durante l'installazione:
::    [X] Add Python to PATH
::    [X] Install for current user only (se appare la voce)

:: 2. Verifica Python
python --version

:: 3. Installa ola
cd C:\Users\TuoNome\Desktop\ollama-agent
install.bat

:: Se install.bat fallisce su Ollama, salta quella parte:
pip install --user .
```

### PC aziendali con policy restrittive

Attenzione: su molti PC aziendali, oltre al "non sei admin" ci possono essere **ulteriori blocchi**:

| Restrizione | Sintomo | Workaround |
|---|---|---|
| **AppLocker / WDAC** | `python.exe` bloccato dall'esecuzione | Serve richiesta formale all'IT |
| **Antivirus aziendale** | Blocca download `.exe` o DLL di Whisper | Usa solo provider cloud via API |
| **Firewall corporate** | Blocca `ollama.com`, `huggingface.co` | Usa provider cloud (Groq/OpenAI/OpenRouter) |
| **Proxy HTTPS con MITM** | `pip install` fallisce su SSL | `pip config set global.cert <path/a/cert.pem>` |
| **Script disabilitati** | `install.bat` o PowerShell bloccati | Installa a mano con `pip install --user .` |

### Setup "minimo robusto" per ambienti restrittivi

Se sospetti restrizioni pesanti, questa rotta usa **solo Python + pip + HTTPS** verso cloud, senza servizi locali:

```bash
pip install --user .
export OPENAI_API_KEY=sk-...      # o GROQ_API_KEY, OPENROUTER_API_KEY
ola -p openai                      # oppure -p groq, -p openrouter
```

Nessun servizio in background, nessun driver, nessun socket locale. È il profilo più compatibile con PC aziendali bloccati.

### Riepilogo funzionalità senza admin

| Funzionalità | Linux (no sudo) | Windows (no admin) |
|---|---|---|
| ola + provider cloud (Groq/OpenAI/OpenRouter) | ✅ | ✅ |
| Ollama locale | ❌ | ✅ (installer recente) |
| Comando `/voice` (microfono) | ❌ | ✅ |
| Server MCP via `npx` | ✅ (con nvm) | ✅ |
| RAG (`/learn`, `/ask`) | ⚠️ serve servizio embedding | ✅ se installi Ollama |
| Sessioni (`/save`, `/resume`) | ✅ | ✅ |

**In sintesi:** su entrambi i sistemi ola funziona benissimo senza admin se usi un provider cloud. Su Windows hai anche accesso a Ollama locale e `/voice` senza admin. Linux è più restrittivo sulle dipendenze di sistema.

---

## Avvio rapido

### Con Ollama (predefinito)

Assicurati che Ollama sia in esecuzione, poi:

```bash
ola
```

Nessuna API key richiesta per i modelli Ollama. Il modello predefinito è `deepseek-v3.1:671b-cloud` (cloud).

Per usare un modello locale:

```bash
ola -m qwen2.5-coder:7b
```

La scelta del modello e del provider viene **salvata automaticamente** e ricordata al prossimo avvio (vedi [Persistenza delle preferenze](#persistenza-delle-preferenze)).

### Prompt singolo (non interattivo)

```bash
ola "Spiega cosa fa questa funzione"
ola "Scrivi un test per il file main.py"
```

Utile per pipe e script:

```bash
cat errore.log | ola "Cosa significa questo errore?"
```

---

## Provider supportati

| Provider | Flag | Modello predefinito | Variabile d'ambiente |
|---|---|---|---|
| **Ollama** *(default)* | `-p ollama` | `deepseek-v3.1:671b-cloud` | — |
| OpenAI | `-p openai` | `gpt-4o` | `OPENAI_API_KEY` |
| Groq | `-p groq` | `llama-3.3-70b-versatile` | `GROQ_API_KEY` |
| OpenRouter | `-p openrouter` | `anthropic/claude-3.5-sonnet` | `OPENROUTER_API_KEY` |

Ollama è il provider **predefinito** e supporta due modalità:

- **Modelli cloud** (tag `:cloud`): girano su infrastruttura Ollama, non richiedono GPU né spazio su disco
- **Modelli locali**: girano interamente sul tuo PC, i dati non escono mai dalla tua macchina

Per i modelli locali è necessario che il modello supporti il tool calling.

Modelli locali consigliati con tool calling:

| Modello | Dimensione | Note |
|---|---|---|
| `qwen2.5-coder:7b` | ~5 GB | Ottimo per il coding |
| `qwen2.5-coder:14b` | ~9 GB | Più preciso |
| `llama3.1:8b` | ~5 GB | Uso generale |
| `mistral-nemo` | ~7 GB | Buon equilibrio |

### Esempi

```bash
# Ollama con un modello specifico
ola -m deepseek-v3.1:671b-cloud

# Modello locale
ola -m qwen2.5-coder:7b

# OpenAI
export OPENAI_API_KEY=sk-...
ola -p openai

# Groq (veloce, tier gratuito disponibile)
export GROQ_API_KEY=gsk_...
ola -p groq

# OpenRouter (accesso a Claude, Gemini, Llama e altri)
export OPENROUTER_API_KEY=sk-or-...
ola -p openrouter -m anthropic/claude-3.5-sonnet

# URL personalizzato (qualsiasi API compatibile OpenAI)
ola --base-url http://mio-server:8080/v1 --api-key chiave
```

### File `.env`

In alternativa alle variabili d'ambiente puoi creare un file `.env` nella directory di lavoro:

```env
OLLAMA_API_KEY=ollama_...
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
OPENROUTER_API_KEY=sk-or-...

# Opzionale: limite settimanale di token (mostra % nella toolbar)
# OLLAMA_AGENT_WEEKLY_LIMIT=500000
```

---

## Indicatori visivi

Durante l'utilizzo, Ollama Agent mostra feedback visivo in tempo reale:

| Situazione | Indicatore |
|---|---|
| In attesa della prima risposta | `⠸ thinking...` (spinner animato) |
| Esecuzione di un tool | `⠸ running bash...` (spinner animato) |
| Tool completato | `✓  output...` |
| Tool rifiutato dall'utente | `✗  Tool execution denied by user.` |
| Richiesta di consenso | `Execute? [Y/n/auto]` |
| Diff preview (edit_file) | Pannello con righe `-` rosse e `+` verdi |
| Write preview (write_file) | Pannello con anteprima contenuto |
| Comando distruttivo (bash) | `⚠ Destructive command detected` |
| Risposta in streaming | Testo che appare carattere per carattere |

La barra in basso mostra sempre modello, consumi della sessione e consumi settimanali:

```
 deepseek-v3.1:671b-cloud  │  session: 4.2k tok  (3.1k in / 1.1k out)  │  weekly: 28.5k tok
```

Il conteggio **session** si azzera ad ogni riavvio. Il conteggio **weekly** è persistente e si resetta automaticamente all'inizio di ogni settimana (lunedì). I dati settimanali sono salvati in `~/.ollama_agent_usage.json`.

### Limite settimanale (opzionale)

Se imposti un limite settimanale di token, la toolbar mostra anche la percentuale di utilizzo:

```bash
export OLLAMA_AGENT_WEEKLY_LIMIT=500000
```

```
 deepseek-v3.1:671b-cloud  │  session: 4.2k tok  (3.1k in / 1.1k out)  │  weekly: 28.5k tok (6%)
```

---

## Comandi slash

Digita `/` nel prompt per vedere il menu a tendina con completamento automatico (`Tab`).

| Comando | Argomento | Descrizione |
|---|---|---|
| `/help` | | Mostra il pannello dei comandi |
| `/clear` | | Pulisce la cronologia della conversazione |
| `/init` | | Crea il file `AGENT.md` di contesto progetto |
| `/learn` | `<path> [--force]` | Indicizza un file o una cartella (con `--force` reindicizza ignorando i fingerprint) |
| `/ask` | `<file> <domanda>` | Interroga un singolo file indicizzato (scoped, non tocca il resto della KB) |
| `/voice` | | Detta il prompt a voce dal microfono (vedi sezione dedicata) |
| `/lang` | `<it\|en>` | Cambia lingua dell'interfaccia (descrizioni comandi e `/help`) |
| `/mcp` | `<subcmd>` | Gestione server MCP (vedi sezione dedicata) |
| `/web` | `[on\|off\|provider <name>]` | Attiva/disattiva ricerca web o cambia provider (vedi sezione dedicata) |
| `/knowledge` | `[files]` | Mostra le cartelle indicizzate (con `files` elenca anche i singoli file) |
| `/model` | `<nome>` | Mostra o cambia il modello attivo (salvato per provider) |
| `/models` | | Lista i modelli disponibili in Ollama (● = attivo) |
| `/provider` | `<nome>` | Cambia provider (ogni provider ricorda il suo modello) |
| `/routing` | `<mode>` | Cambia modalità routing (`manual`/`auto`/`static`) |
| `/ragmode` | `<mode>` | Cambia modalità RAG (`standard`/`rlm`) — vedi sezione dedicata |
| `/rules` | `[args]` | Gestisci regole routing statico (`list`/`set`/`reset`) |
| `/save` | `[titolo]` | Salva la sessione corrente (titolo auto-generato o personalizzato) |
| `/sessions` | | Lista le sessioni salvate |
| `/resume` | `[#]` | Riprende una sessione salvata (default: la più recente) |
| `/autosave` | | Attiva/disattiva il salvataggio automatico all'uscita |
| `/settings` | | Mostra la configurazione corrente |
| `/tools` | | Lista gli strumenti disponibili |
| `/compact` | | Riassume la conversazione nel modello per liberare token di contesto |
| `/commit` | | Genera un messaggio di commit con l'LLM e fa `git commit` dopo conferma |
| `/undo` | | Annulla l'ultima modifica/scrittura di file fatta dall'agent (stack per sessione) |
| `/costs` | | Mostra costi stimati (sessione + settimana) per provider/modello |
| `/quiet` | | Attiva/disattiva la modalità silenziosa (nasconde i dettagli delle tool call) |
| `/auto` | | Approva automaticamente tutte le operazioni |
| `/manual` | | Chiedi consenso prima di operazioni di scrittura (default) |
| `/exit` | | Esci dal programma |

### Tastiera

| Tasto | Azione |
|---|---|
| `Ctrl+C` | Annulla la risposta in corso |
| `Ctrl+D` | Esci |
| `↑` / `↓` | Naviga la cronologia degli input |
| `Tab` | Completa il comando slash |

---

## Sessioni

Ollama Agent può salvare e riprendere le conversazioni, così puoi continuare il lavoro dove lo avevi lasciato.

### Salvataggio manuale

```bash
/save                    # salva con titolo auto-generato (dal primo messaggio)
/save fix login bug      # salva con titolo personalizzato
```

### Lista e ripresa

```bash
/sessions                # mostra tutte le sessioni salvate
/resume                  # riprende l'ultima sessione
/resume 3                # riprende la sessione #3 dalla lista
```

### Salvataggio automatico

Per attivare il salvataggio automatico all'uscita (Ctrl+D o `/exit`):

```bash
/autosave                # toggle on/off (stato visibile in /settings)
```

Quando attivo, la sessione viene salvata automaticamente ogni volta che esci da ola. Lo stato è persistente tra le sessioni.

### Dettagli tecnici

- Le sessioni sono salvate in `~/.ollama_agent/sessions/` come file JSON
- Ogni sessione registra: messaggi, directory di lavoro, modello, provider, data/ora
- `/resume` ripristina i messaggi e continua la conversazione naturalmente
- `/clear` pulisce solo la conversazione corrente, non elimina le sessioni salvate
- Il titolo auto-generato è il testo del primo messaggio dell'utente (max 60 caratteri)

---

## Routing dei modelli

Ollama Agent supporta tre modalità di routing che determinano come viene scelto il modello per ogni richiesta.

### Modalità manual (default)

Il comportamento classico: usi un solo modello scelto con `/model`. Tutte le richieste vanno allo stesso modello.

```bash
/routing manual
```

### Modalità auto (classificatore)

Un classificatore analizza automaticamente ogni messaggio e lo instrada al modello più adatto. La classificazione è trasparente — vedrai quale categoria è stata assegnata:

```bash
/routing auto

> scrivi una funzione per ordinare una lista
  classifying request...
  routing: code → openrouter/anthropic/claude-3.5-sonnet
```

Le categorie supportate sono: `code`, `debug`, `review`, `docs`, `general`.

In modalità auto, il sistema preferisce i modelli cloud per ottimizzare le performance sui PC meno potenti.

Se un modello locale (Ollama) non è installato, l'agent chiede conferma prima di scaricarlo, dato che i modelli occupano diversi GB di spazio.

### Modalità static (regole manuali)

Definisci tu la mappa task → modello. La classificazione avviene tramite keyword matching (senza chiamate extra al modello).

```bash
/routing static

# Vedi le regole attuali
/rules

# Imposta un modello per una categoria
/rules code=deepseek-coder-v2
/rules docs=llama3.1
/rules debug=anthropic/claude-3.5-sonnet

# Reset ai valori predefiniti
/rules reset
```

Le regole vengono salvate permanentemente in `~/.ollama_agent_prefs.json`.

### Categorie di task

| Categoria | Quando viene usata |
|---|---|
| `code` | Generazione codice, refactoring, implementazione feature |
| `debug` | Fix bug, analisi errori, troubleshooting |
| `review` | Code review, analisi qualità, suggerimenti |
| `docs` | Documentazione, spiegazioni, tutorial |
| `general` | Tutto il resto |

### Formato modelli nelle regole

| Formato | Provider | Esempio |
|---|---|---|
| `nome-modello` | Ollama (locale) | `deepseek-coder-v2`, `llama3.1` |
| `org/nome-modello` | OpenRouter (cloud) | `anthropic/claude-3.5-sonnet` |
| `gpt-*` | OpenAI | `gpt-4o` |

Il provider viene rilevato automaticamente dal formato del nome. Dopo ogni risposta, il modello torna a quello base configurato.

### Suggerimenti modelli per categoria

Di seguito una panoramica dei modelli consigliati per ogni categoria di task, divisi tra locali (Ollama) e cloud (OpenRouter/OpenAI). La scelta dipende dalle risorse del tuo PC e dalla complessità del lavoro.

#### Code — Generazione e refactoring codice

| Modello | Tipo | Dimensione | Note |
|---|---|---|---|
| `deepseek-coder-v2` | Ollama | ~8 GB | Ottimo per codice, supporta molti linguaggi |
| `deepseek-coder-v2:16b` | Ollama | ~16 GB | Versione più capace |
| `codellama:13b` | Ollama | ~7 GB | Specializzato in codice, buono per completamenti |
| `codellama:34b` | Ollama | ~19 GB | Versione pesante ma molto precisa |
| `qwen2.5-coder:7b` | Ollama | ~4.5 GB | Leggero e veloce, buon rapporto qualità/peso |
| `qwen2.5-coder:32b` | Ollama | ~18 GB | Eccellente per codice complesso |
| `starcoder2:15b` | Ollama | ~9 GB | Addestrato su The Stack v2, multi-linguaggio |
| `anthropic/claude-3.5-sonnet` | OpenRouter | Cloud | Top per codice complesso e refactoring |
| `anthropic/claude-3-haiku` | OpenRouter | Cloud | Veloce e economico, buono per task semplici |
| `google/gemini-pro-1.5` | OpenRouter | Cloud | Contesto molto ampio (1M token) |
| `gpt-4o` | OpenAI | Cloud | Eccellente per codice, molto versatile |
| `gpt-4o-mini` | OpenAI | Cloud | Veloce e economico |

#### Debug — Fix bug e troubleshooting

| Modello | Tipo | Dimensione | Note |
|---|---|---|---|
| `deepseek-coder-v2` | Ollama | ~8 GB | Buono nell'analisi degli errori |
| `qwen2.5:14b` | Ollama | ~8 GB | Ragionamento solido per debug |
| `qwen2.5:32b` | Ollama | ~18 GB | Ottimo ragionamento, analisi profonda |
| `llama3.1:8b` | Ollama | ~4.7 GB | Leggero, sufficiente per bug semplici |
| `anthropic/claude-3.5-sonnet` | OpenRouter | Cloud | Eccellente per debug complesso, ragionamento step-by-step |
| `openai/o1-mini` | OpenRouter | Cloud | Specializzato in ragionamento, ideale per bug difficili |
| `gpt-4o` | OpenAI | Cloud | Molto preciso nell'identificare problemi |

#### Review — Code review e analisi qualità

| Modello | Tipo | Dimensione | Note |
|---|---|---|---|
| `qwen2.5:14b` | Ollama | ~8 GB | Buon bilanciamento per review |
| `qwen2.5:32b` | Ollama | ~18 GB | Review approfondite e dettagliate |
| `deepseek-coder-v2` | Ollama | ~8 GB | Conosce bene i pattern di codice |
| `anthropic/claude-3.5-sonnet` | OpenRouter | Cloud | Migliore per review approfondite, cattura edge case |
| `google/gemini-pro-1.5` | OpenRouter | Cloud | Contesto enorme, ottimo per review di file grandi |
| `gpt-4o` | OpenAI | Cloud | Preciso e dettagliato nelle osservazioni |

#### Docs — Documentazione e spiegazioni

| Modello | Tipo | Dimensione | Note |
|---|---|---|---|
| `llama3.1:8b` | Ollama | ~4.7 GB | Leggero, scrive bene in italiano e inglese |
| `llama3.1:70b` | Ollama | ~40 GB | Eccellente qualità di scrittura |
| `mistral:7b` | Ollama | ~4 GB | Veloce, buono per docs brevi |
| `mixtral:8x7b` | Ollama | ~26 GB | Multilingue, ottimo per documentazione |
| `qwen2.5:7b` | Ollama | ~4.5 GB | Buono per spiegazioni tecniche |
| `anthropic/claude-3.5-sonnet` | OpenRouter | Cloud | Eccellente per documentazione tecnica e tutorial |
| `anthropic/claude-3-haiku` | OpenRouter | Cloud | Veloce per docs semplici |
| `gpt-4o` | OpenAI | Cloud | Molto fluido nella scrittura |
| `gpt-4o-mini` | OpenAI | Cloud | Economico per docs di routine |

#### General — Conversazione e task misti

| Modello | Tipo | Dimensione | Note |
|---|---|---|---|
| `llama3.1:8b` | Ollama | ~4.7 GB | Versatile e leggero |
| `qwen2.5:7b` | Ollama | ~4.5 GB | Rapido per risposte generali |
| `mistral:7b` | Ollama | ~4 GB | Veloce, risposte concise |
| `gemma2:9b` | Ollama | ~5.4 GB | Buon tuttofare |
| `phi3:14b` | Ollama | ~7.9 GB | Sorprendentemente capace per le dimensioni |
| `anthropic/claude-3-haiku` | OpenRouter | Cloud | Veloce e economico |
| `gpt-4o-mini` | OpenAI | Cloud | Buon compromesso velocità/qualità |

#### Esempi di configurazione consigliata

**PC con poca RAM (8-16 GB) — preferisci cloud:**
```bash
/rules code=anthropic/claude-3.5-sonnet
/rules debug=anthropic/claude-3.5-sonnet
/rules review=anthropic/claude-3.5-sonnet
/rules docs=gpt-4o-mini
/rules general=anthropic/claude-3-haiku
```

**PC con GPU media (16-24 GB VRAM) — mix locale/cloud:**
```bash
/rules code=deepseek-coder-v2
/rules debug=anthropic/claude-3.5-sonnet
/rules review=qwen2.5:14b
/rules docs=llama3.1:8b
/rules general=llama3.1:8b
```

**PC potente (32+ GB VRAM) — tutto in locale:**
```bash
/rules code=qwen2.5-coder:32b
/rules debug=qwen2.5:32b
/rules review=qwen2.5:32b
/rules docs=llama3.1:70b
/rules general=llama3.1:8b
```

---

## Consenso e preview delle modifiche

Per impostazione predefinita, Ollama Agent chiede il consenso dell'utente prima di eseguire operazioni che modificano il sistema. Le operazioni di sola lettura vengono eseguite automaticamente.

### Operazioni che richiedono consenso

| Operazione | Preview |
|---|---|
| `bash` (qualsiasi comando shell) | Avviso speciale per comandi distruttivi (`rm`, `rmdir`, ecc.) |
| `write_file` (creazione/sovrascrittura file) | Anteprima del contenuto con indicazione "new file" o "overwrite" |
| `edit_file` (modifica di un file) | **Diff colorato** con righe rosse (rimosse) e verdi (aggiunte) |

### Operazioni sempre approvate (sola lettura)

`read_file`, `list_dir`, `grep`, `find_files`, `search_knowledge`

### Esempio di diff preview

Quando l'agent vuole modificare un file, viene mostrata un'anteprima prima dell'esecuzione:

```
╭────────────────── Diff preview ──────────────────╮
│   main.py                                         │
│   - def hello():                                  │
│   -     print("hello")                            │
│   + def hello(name: str):                         │
│   +     print(f"hello {name}")                    │
│   +     return name                               │
╰───────────────────────────────────────────────────╯
  Execute? [Y/n/auto]
```

### Risposte al prompt di consenso

| Risposta | Effetto |
|---|---|
| `Y` o `Invio` | Approva l'operazione |
| `n` | Rifiuta — l'agent viene informato e può adattarsi |
| `auto` | Approva questa e tutte le operazioni successive (equivale a `/auto`) |

### Modalità auto/manual

- `/auto` — disattiva la richiesta di consenso per tutta la sessione
- `/manual` — riattiva la richiesta di consenso (default)

La modalità è visibile in `/settings`.

---

## Persistenza delle preferenze

Ollama Agent salva automaticamente la scelta di **provider** e **modello** nel file `~/.ollama_agent_prefs.json`. Le preferenze vengono ricordate tra una sessione e l'altra.

### Come funziona

- Ogni **provider** memorizza il proprio modello separatamente
- Quando cambi modello con `/model`, la scelta viene salvata per il provider attivo
- Quando cambi provider con `/provider`, viene ripristinato l'ultimo modello usato con quel provider
- Se non hai mai usato un provider, viene usato il suo modello predefinito

### Esempio pratico

```
> /model llama3                 # ollama ora usa llama3 (salvato)
> /provider openai              # passa a openai con gpt-4o (suo default)
> /model gpt-4o-mini            # openai ora usa gpt-4o-mini (salvato)
> /provider ollama              # torna a ollama → riprende llama3 ✓
```

Alla prossima apertura di `ola`, verranno usati l'ultimo provider e l'ultimo modello selezionati.

### Priorità di configurazione

Il modello attivo viene determinato in questo ordine (il primo trovato vince):

1. Flag CLI esplicito (`ola -m <modello>` o `ola -p <provider>`)
2. Variabile d'ambiente (`OLLAMA_CODE_MODEL`, `OLLAMA_CODE_PROVIDER`)
3. Preferenza salvata (`~/.ollama_agent_prefs.json`)
4. Default del provider (es. `deepseek-v3.1:671b-cloud` per Ollama)

### File delle preferenze

```json
{
  "provider": "ollama",
  "models": {
    "ollama": "llama3",
    "openai": "gpt-4o-mini",
    "groq": "llama-3.3-70b-versatile"
  }
}
```

> **Nota:** i flag CLI (`-m`, `-p`) sovrascrivono le preferenze salvate solo per quella sessione, senza modificarle. Per salvare una nuova preferenza in modo permanente, usa i comandi `/model` e `/provider` all'interno della sessione interattiva.

---

## Il comando `/init` e il contesto progetto (AGENT.md)

Il comando `/init` crea un file **`AGENT.md`** nella directory corrente. Questo file serve da "scheda progetto" che ola legge automaticamente ad ogni messaggio, dandogli il contesto necessario per capire il progetto su cui stai lavorando.

### Perché usare `/init`

Senza `AGENT.md`, il modello parte "alla cieca" — non sa che linguaggio usi, quali convenzioni segui, qual è l'architettura del progetto. Con `AGENT.md` compilato bene, le risposte diventano immediatamente pertinenti al tuo contesto.

### Come funziona

1. Entra nella cartella del tuo progetto: `cd /home/daniele/mio-progetto`
2. Avvia ola: `ola`
3. Digita `/init`
4. Ola crea `AGENT.md` con un template vuoto da compilare
5. Apri il file con il tuo editor e compilalo
6. Da quel momento, **ogni messaggio** che invii a ola include automaticamente il contenuto di `AGENT.md` come contesto

### Cosa succede internamente

- `/init` crea il file solo se **non esiste già** — non sovrascrive mai un `AGENT.md` esistente
- Dopo la creazione, chiama `refresh_context()` per caricarlo subito nella sessione
- Il file viene **riletto ad ogni messaggio**, quindi puoi modificarlo mentre ola è in esecuzione e le modifiche sono immediate
- Il contenuto viene iniettato come messaggio di sistema, prima dei tuoi messaggi

### Template generato

```markdown
# Project context

<!-- Describe the project so Ollama Agent understands it from the start. -->

## Description


## Stack


## Conventions


## Notes

```

### Esempio compilato

```markdown
# Project context

## Description
API REST in FastAPI per la gestione degli ordini e-commerce.
Supporta autenticazione JWT, pagamenti Stripe e notifiche email.

## Stack
- Python 3.11, FastAPI, SQLAlchemy 2.0, PostgreSQL 15
- pytest per i test, alembic per le migrazioni
- Docker Compose per lo sviluppo locale
- Redis per caching e code

## Conventions
- Snake case per funzioni e variabili, PascalCase per le classi
- Tutti gli endpoint restituiscono `{ data, error, meta }`
- I test vanno in `tests/` con prefisso `test_`
- Ogni PR deve avere almeno un test
- Commit messages in inglese, formato conventional commits

## Notes
- Il database di produzione è su AWS RDS
- Non toccare le migrazioni già applicate in prod (da 001 a 042)
- Il modulo `payments/` è in fase di refactoring — chiedere prima di modificarlo
```

### Suggerimenti

- **Sii specifico**: "Python 3.11" è meglio di "Python"; "snake_case" è meglio di "segui le convenzioni"
- **Includi le cose non ovvie**: le convenzioni che non si capiscono leggendo il codice
- **Aggiorna il file**: quando cambia lo stack o le convenzioni, aggiorna `AGENT.md`
- **Un file per progetto**: ogni cartella può avere il suo `AGENT.md` — ola legge quello della directory corrente

Il modello riceve anche automaticamente la **directory di lavoro corrente** e il **branch/status git** (se disponibile).

---

## Leggere file in una cartella (senza RAG)

Prima ancora di usare il RAG, Ollama Agent può **guardare direttamente dentro una cartella** grazie ai suoi tool di lettura. Se nel prompt indichi un percorso di cartella, il modello lo esplora da solo con `list_dir`, `find_files`, `grep` e `read_file` per rispondere alla tua domanda. Nessuna indicizzazione è necessaria.

```
> nella cartella /home/daniele/progetto-x ci sono dei file .py e .md, guardaci dentro e dimmi quali parlano di autenticazione
```

L'agent procederà tipicamente così:

1. `list_dir` sulla cartella per vedere cosa contiene
2. `find_files` o `grep` per individuare i file che contengono le parole chiave
3. `read_file` sui file rilevanti per leggerli completamente
4. Formula la risposta in base al contenuto letto

### Quando preferire questa modalità

| Scenario | Meglio usare |
|---|---|
| Poche unità di file testuali (< 10-20) | **Lettura diretta** (senza RAG) |
| Dati sempre in cambiamento, vuoi freschezza totale | **Lettura diretta** |
| Tanti file, o documenti voluminosi | **RAG** con `/learn` |
| PDF, DOCX, XLSX | **RAG** (`read_file` legge solo testo) |
| Domande ricorrenti sullo stesso corpus | **RAG** (più veloce, meno contesto) |

### Limiti

- `read_file` **legge solo formati testuali** (codice, `.md`, `.txt`, `.json`, ecc.). PDF, Word ed Excel devono passare dal RAG.
- Il contenuto dei file letti finisce nel contesto del modello: con cartelle grandi si rischia di saturare la finestra. Il RAG è più scalabile in questi casi.
- Ogni nuova conversazione ripete il lavoro di lettura: se fai molte domande sugli stessi file, `/learn` è più efficiente.

---

## Supporto immagini e OCR

Ollama Agent accetta immagini come input: basta **incollare o trascinare** il percorso del file nel prompt (la maggior parte dei terminali inserisce automaticamente il path di un file trascinato).

```
> /home/daniele/Immagini/screenshot.png cosa significa questo errore?
> analizza grafico.jpg e spiegami il trend
> "/path/con spazi/diagramma.png" estrai il testo OCR da questa immagine
```

Formati supportati: `.png` `.jpg` `.jpeg` `.gif` `.webp` `.bmp`

### Come funziona

1. L'agent rileva automaticamente i percorsi di file immagine nel tuo messaggio
2. Li rimuove dal testo e li codifica in **base64** come data URL
3. Costruisce un messaggio multimodale (testo + immagine) secondo lo standard OpenAI
4. Viene mostrato un indicatore `📎 attached: nome-file.png` per ogni immagine riconosciuta

Le immagini **non vengono salvate da nessuna parte**: sono inviate direttamente al modello e poi restano solo nella cronologia della conversazione in memoria (cancellata al `/clear` o alla chiusura della sessione).

### Modelli che supportano immagini e OCR

Non tutti i modelli sono capaci di "vedere". Per usare le immagini devi selezionare un modello con capacità **vision**. In particolare per l'**OCR** (estrazione di testo da immagini) servono modelli allenati anche su testo stampato/manoscritto.

#### Modelli vision locali (Ollama)

| Modello | Dimensione | Vision | OCR | Note |
|---|---|---|---|---|
| `llava:7b` | ~4.7 GB | Sì | Base | Il classico vision model di Ollama, OCR semplice |
| `llava:13b` | ~8 GB | Sì | Base | Più preciso del 7b |
| `llava:34b` | ~20 GB | Sì | Buono | Qualità vicina ai modelli cloud |
| `llama3.2-vision:11b` | ~7.8 GB | Sì | Buono | Vision di Meta, buono per descrizioni e OCR |
| `llama3.2-vision:90b` | ~55 GB | Sì | Ottimo | Top di gamma locale |
| `bakllava` | ~4.7 GB | Sì | Base | Variante di LLaVA basata su Mistral |
| `moondream` | ~1.7 GB | Sì | Base | Modello leggerissimo, adatto a macchine limitate |
| `minicpm-v` | ~5.5 GB | Sì | **Ottimo** | Eccellente per OCR, supporta molte lingue |
| `qwen2.5vl:7b` | ~6 GB | Sì | **Ottimo** | Vision di Alibaba, OCR e ragionamento visivo forti |
| `qwen2.5vl:32b` | ~19 GB | Sì | **Ottimo** | Versione più capace |
| `granite3.2-vision` | ~2.4 GB | Sì | Buono | IBM, orientato a documenti e tabelle |

#### Modelli vision cloud (OpenRouter / OpenAI)

| Modello | Tipo | Vision | OCR | Note |
|---|---|---|---|---|
| `anthropic/claude-3.5-sonnet` | OpenRouter | Sì | **Ottimo** | Lettura accurata di screenshot, diagrammi, testo |
| `anthropic/claude-3-opus` | OpenRouter | Sì | **Ottimo** | Massima precisione, più lento e costoso |
| `anthropic/claude-3-haiku` | OpenRouter | Sì | Buono | Economico, buono per OCR di base |
| `google/gemini-pro-1.5` | OpenRouter | Sì | **Ottimo** | Eccellente OCR multilingua, contesto enorme |
| `google/gemini-flash-1.5` | OpenRouter | Sì | Buono | Veloce ed economico |
| `openai/gpt-4o` | OpenRouter | Sì | **Ottimo** | Top per analisi visiva e OCR |
| `openai/gpt-4o-mini` | OpenRouter | Sì | Buono | Economico, ottimo rapporto qualità/prezzo |
| `gpt-4o` | OpenAI | Sì | **Ottimo** | Uguale ma diretto via API OpenAI |
| `gpt-4o-mini` | OpenAI | Sì | Buono | Veloce ed economico |

> **Suggerimento:** se devi fare principalmente **OCR da PDF scannerizzati, screenshot o fotografie di documenti**, i migliori in locale sono `minicpm-v` e `qwen2.5vl`, mentre in cloud Claude 3.5 Sonnet, Gemini 1.5 Pro e GPT-4o offrono i risultati più affidabili.

### Esempio di uso con modello vision

```bash
# Cambia a un modello vision prima di inviare l'immagine
/model llava:13b
> /home/daniele/Scrivania/errore.png cosa mostra questo screenshot?

# Oppure in cloud con Claude per qualità OCR massima
/provider openrouter
/model anthropic/claude-3.5-sonnet
> /path/scansione.jpg estrai tutto il testo presente nell'immagine
```

Se invii un'immagine a un modello **non vision**, il provider restituirà un errore: basta cambiare modello con `/model` e riprovare.

---

## Knowledge base (RAG)

Ollama Agent include un sistema RAG (Retrieval Augmented Generation) che permette di indicizzare documenti e farli consultare al modello automaticamente.

### Setup

Il modello di embedding (`granite-embedding:30m`) viene scaricato automaticamente durante l'installazione o al primo utilizzo di `/learn`. Non è necessaria alcuna configurazione manuale.

### Utilizzo

```bash
# Indicizza una cartella intera (ricorsivo: include tutte le sottocartelle)
/learn ./docs

# Indicizza un singolo file
/learn ./architettura.md
/learn ./api-reference.pdf

# Vedi cosa è indicizzato
/knowledge
```

**Scansione ricorsiva automatica:** quando passi una cartella a `/learn`, il sistema scansiona automaticamente tutte le sottocartelle a qualsiasi livello di profondità. Non serve usare glob o wildcard — basta indicare la cartella radice.

```
docs/
├── guida.md            ← indicizzato
├── api/
│   ├── rest.md         ← indicizzato
│   └── graphql.md      ← indicizzato
└── report/
    └── analisi.pdf     ← indicizzato
```

```bash
/learn ./docs           # indicizza tutto: guida.md, rest.md, graphql.md, analisi.pdf
```

Le seguenti cartelle vengono **ignorate automaticamente**: `.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `.mypy_cache`, `dist`, `build`, `.next`, `.nuxt`.

Da quel momento il modello usa il tool `search_knowledge` autonomamente quando ritiene utile consultare la knowledge base, senza che tu debba chiederlo esplicitamente.

### Come funziona

1. `/learn` scansiona ricorsivamente la cartella e per ogni file:
   - **Estrae il testo** (PDF via pypdf, DOCX via python-docx, XLSX via openpyxl, testo semplice per il resto)
   - **Normalizza** il testo: unisce le righe spezzate dai PDF multicolonna, ricompone le parole tagliate a fine riga con il trattino (`cyberse-\ncurity` → `cybersecurity`), preserva i confini di paragrafo
   - **Spezza in chunk** di ~350 parole rispettando i confini dei paragrafi (mai tagli in mezzo a una frase); se un paragrafo eccede la soglia, fallback allo split per frasi
   - **Sovrappone** ogni chunk al successivo di ~50 parole per non perdere il contesto
   - **Prefissa** ogni chunk con `[File: nome-del-file]` così l'embedding cattura anche il contesto del file sorgente (fondamentale per domande che nominano esplicitamente un file)
2. I chunk vengono inviati in **parallelo** (4 richieste concorrenti) a `granite-embedding:30m` per la trasformazione in vettori — ~10× più veloce del precedente modello nomic-embed-text
3. I vettori vengono salvati in `~/.ollama_agent/knowledge/global/store.json` — **una sola knowledge base globale** condivisa tra tutti i progetti (i file sono identificati dal loro path assoluto, quindi non si mescolano)
4. Ad ogni domanda, la query viene anch'essa vettorizzata e confrontata con i chunk via similarità coseno
5. I 5 chunk più rilevanti (o 10 quando la domanda riguarda un file specifico) vengono iniettati nel contesto della risposta (max 6000 caratteri per evitare overflow)

Gli **embedding restano sempre sul tuo PC** — niente va in cloud.

### Ricerca mirata per file

Quando la domanda riguarda un file specifico (es. *"di cosa tratta il file McMillan_Cybersecurity.pdf?"*), il modello passa automaticamente il nome del file come `source_filter` al tool `search_knowledge`. La ricerca viene così ristretta **solo a quel file**, restituendo fino a 10 chunk anziché 5 per dare al modello un contesto più ampio per rispondere.

Se il filtro non matcha nessun file, viene restituito un messaggio di errore con la lista dei file disponibili, così il modello può riprovare con il nome corretto.

### Protezione file indicizzati

Una volta che un file è nella knowledge base, l'agent **non può leggerlo direttamente** — né con `read_file`, né con comandi bash come `cat`, `head`, `strings`, ecc. Questo evita che il modello tenti di caricare in contesto file enormi (es. PDF da centinaia di pagine). Le risposte si basano esclusivamente sui chunk estratti tramite `search_knowledge`.

### Indicizzazione incrementale

La knowledge base è **persistente** e **incrementale**: una volta indicizzata una cartella, i dati restano su disco e non serve ri-indicizzare ad ogni avvio.

Quando rilanci `/learn` sulla stessa cartella, il sistema confronta un fingerprint (hash MD5) di ogni file con quello salvato nell'indicizzazione precedente e:

- **File invariati** → saltati (nessun lavoro)
- **File nuovi** → indicizzati
- **File modificati** → chunk vecchi rimossi e ri-generati
- **File cancellati dal disco** → rimossi automaticamente dalla knowledge base

```bash
# Prima indicizzazione: processa tutto
/learn ./docs
#   Found 87 file(s): 87 new
#   ✓ Indexed 87 file(s) → 234 chunks

# Seconda volta, nulla cambiato: istantaneo
/learn ./docs
#   Found 87 file(s): 87 unchanged
#   ✓ Knowledge base already up to date — nothing to re-index

# Dopo aver modificato 3 file e aggiunto 1 nuovo
/learn ./docs
#   Found 88 file(s): 1 new, 3 modified, 84 unchanged
#   ✓ Indexed 4 file(s) → 12 chunks
```

### Forzare il reindex (`--force`)

Se vuoi **reindicizzare da zero** tutti i file di una cartella — per esempio dopo un aggiornamento del chunker che migliora la qualità delle estrazioni — usa il flag `--force`:

```bash
# Re-indicizza tutto, ignorando i fingerprint
/learn /home/daniele/Scrivania/PDF/it --force

# Alias accettati: -f, force
/learn ./docs -f
```

Quando usi `--force`, tutti i file sotto quel path vengono trattati come "modificati", i vecchi chunk vengono rimossi e rigenerati con le nuove regole di chunking. Se in precedenza avevi indicizzato PDF con una versione vecchia del chunker, **ti consigliamo di rieseguire `/learn <path> --force`** una volta per beneficiare dei miglioramenti di qualità sulle ricerche.

### Progresso visuale

Durante l'indicizzazione viene mostrata una barra di avanzamento con percentuale, tempo trascorso e tempo stimato rimanente (ETA):

```
⠋ Scanning directory...
  Found 88 file(s): 1 new, 3 modified, 84 unchanged
  Loading embed model...
⠋ ↳ utils.py   ██████████████████░░░░░░░░░░░░  2/4  50.0%  0:00:03  ETA 0:00:03
```

### Due modelli, un solo comando

```
Tu parli con:      deepseek / qwen / llama  ← modello chat (scegli tu)
RAG usa in bg:     granite-embedding:30m     ← solo per embedding, automatico
```

### Formati supportati

**Documenti**

| Formato | Estensione | Note |
|---|---|---|
| PDF | `.pdf` | Estrae testo pagina per pagina |
| Word | `.docx` | Estrae paragrafi e tabelle |
| Excel | `.xlsx` | Estrae celle foglio per foglio |

**Codice e testo**

`.py` `.js` `.ts` `.jsx` `.tsx` `.java` `.go` `.rs` `.c` `.cpp` `.h` `.cs` `.rb` `.php` `.swift` `.kt` `.md` `.txt` `.rst` `.json` `.yaml` `.yml` `.toml` `.html` `.css` `.sh`

### Variabile d'ambiente

Per usare un modello di embedding diverso:

```bash
export OLLAMA_EMBED_MODEL=mxbai-embed-large
```

---

## Modalità RAG: standard vs RLM

Ola supporta **due modalità di retrieval** dalla knowledge base, selezionabili al volo con il comando `/ragmode`:

| Modalità | Come funziona | Velocità | Quando usarla |
|---|---|---|---|
| `standard` *(default)* | Top-k retrieval classico: embedding della domanda, ricerca per similarità coseno, restituisce i **k chunk più simili** | ⚡ Istantaneo | Domande puntuali, lookup factoid, la maggior parte dei casi |
| `rlm` | **Recursive Language Model**: legge **tutti i chunk** dei file selezionati e usa l'LLM stesso per estrarre le parti rilevanti, in parallelo, ricorsivamente | 🐢 Più lento (N chiamate LLM) | Documenti lunghi, domande comparative, sintesi globale, quando il top-k perde il quadro d'insieme |

### Come funziona RLM

La tecnica è ispirata ai **Recursive Language Models (MIT, 2025)**: invece di affidarsi alla sola similarità vettoriale, l'LLM viene invocato ricorsivamente su porzioni del contesto per filtrare ciò che è davvero rilevante.

Pipeline in ola:
1. Raccoglie **tutti** i chunk (eventualmente filtrati per nome file).
2. Raggruppa per documento sorgente.
3. Per ogni documento: se i chunk entrano in un singolo prompt, li lascia grezzi; altrimenti li spezza in batch e per **ogni batch** fa una chiamata LLM che estrae solo le parti rilevanti alla domanda.
4. Le estrazioni vengono aggregate per file e tornano all'agent, che formula la risposta finale.

Non richiede **nessuna libreria esterna** (niente mem0, niente LangChain): usa l'LLM già configurato e il retriever esistente. Il RAG standard resta invariato e rimane il default — RLM è opt-in.

### Comandi

```bash
/ragmode                   # mostra modalità corrente
/ragmode rlm               # passa a retrieval ricorsivo
/ragmode standard          # torna a top-k (default)
```

La modalità scelta è **persistente** (salvata in `~/.ollama_agent_prefs.json`) e visibile in `/settings`. Il modello, all'interno della conversazione, usa lo strumento `search_knowledge` in modalità standard e lo strumento `deep_query` in modalità RLM.

### Quando passare a RLM

- 📄 Documento molto lungo dove la top-k taglia contesto critico
- 🔍 Domande del tipo "riassumi tutto", "confronta X e Y", "qual è il filo conduttore"
- 🤔 Risposte sospette che sembrano mancare di parti del documento

Per domande veloci resta su `standard` — RLM costa tempo e token.

---

## Input vocale (`/voice`)

Puoi dettare i prompt invece di scriverli: il comando `/voice` registra dal microfono, trascrive localmente con **faster-whisper** e invia il testo a ola come se lo avessi digitato.

### Installazione

Le dipendenze vocali (**faster-whisper**, **sounddevice**, **numpy**) vengono installate automaticamente da `install.sh`/`install.bat`. Su Linux Debian/Ubuntu lo script installa anche la libreria di sistema `libportaudio2` (serve a sounddevice).

Se hai installato a mano e vuoi aggiungerle dopo:

```bash
pip install faster-whisper sounddevice numpy
# su Linux Debian/Ubuntu, se serve:
sudo apt install libportaudio2
```

Al primo uso, `faster-whisper` scarica automaticamente il modello (~500 MB per `small`). Il download avviene una sola volta e viene cachato in `~/.cache/huggingface/`.

### Utilizzo

```
> /voice
🎙️  Parla ora — premi Invio per terminare la registrazione...
[parli al microfono]
[premi Invio]
Trascrizione: riassumi il file retriever.py
[ola elabora come se avessi digitato]
```

### Caratteristiche

- **100% locale**: audio e trascrizione non escono dalla tua macchina (niente cloud, niente API esterne)
- **Italiano**: lingua predefinita
- **VAD (Voice Activity Detection)**: silenzi iniziali/finali vengono ignorati
- **Modello cached**: il primo `/voice` è lento (caricamento modello in RAM), i successivi sono istantanei

### Personalizzazione

Per cambiare lingua o taglia del modello, al momento va fatto editando `voice.py`. Modelli disponibili: `tiny`, `base`, `small` (default), `medium`, `large-v3`. Più grande = più accurato ma più lento.

---

## Server MCP (Model Context Protocol)

Ola supporta **server MCP** per estendere i propri tool collegandosi a servizi esterni (filesystem, GitHub, Slack, database…) usando il protocollo standard di Anthropic. I tool esposti dai server MCP si aggiungono a quelli built-in di ola — nessuna sostituzione, tutto additivo.

### Come funziona

1. Al primo avvio ola cerca `~/.ollama_agent_mcp.json`. Se non esiste parte senza server MCP.
2. Per ogni server **enabled** nel file, ola lancia un subprocess e apre una connessione stdio.
3. Chiede al server la lista dei suoi tool → li registra con namespace `mcp__<server>__<tool>` così non entrano mai in conflitto con i tool nativi.
4. Quando il modello chiama un tool con prefisso `mcp__...`, ola lo instrada al server corrispondente.

### Config file

Formato compatibile Claude Desktop:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/utente"],
      "enabled": true
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_..."},
      "enabled": true
    }
  }
}
```

Il file è modificabile a mano oppure tramite i comandi `/mcp add` / `/mcp remove`.

### Comandi `/mcp`

| Comando | Cosa fa |
|---|---|
| `/mcp list` | Mostra i server configurati, stato (connesso/disabilitato/errore) e numero di tool esposti |
| `/mcp tools` | Elenca tutti i tool MCP disponibili, raggruppati per server |
| `/mcp enable <nome>` | Abilita un server e salva il config (serve `/mcp reload` per applicare) |
| `/mcp disable <nome>` | Disabilita un server senza rimuoverlo |
| `/mcp add <nome> <comando> [args...]` | Aggiunge un nuovo server al config |
| `/mcp remove <nome>` | Rimuove un server dal config |
| `/mcp reload` | Riavvia tutti i server MCP (dopo modifiche manuali o toggle enable/disable) |

### Esempio pratico

```bash
# Aggiungi il server filesystem
> /mcp add filesystem npx -y @modelcontextprotocol/server-filesystem /home/daniele

# Riavvia per caricarlo
> /mcp reload
✓ 1 server connessi, 14 tool disponibili

# Verifica
> /mcp tools

# Ora puoi usarlo naturalmente nella conversazione
> elenca i file nella mia home directory
  # → ola chiama automaticamente mcp__filesystem__list_directory
```

### Spiegazione dettagliata del comando `/mcp add`

La sintassi è:

```
/mcp add <nome> <comando> [argomenti...]
```

Dove:
- **`<nome>`** — un'etichetta a tua scelta per identificare il server (es. `filesystem`, `github`, `mydb`)
- **`<comando>`** — il programma da avviare (es. `npx`, `python`, `node`, `uvx`)
- **`[argomenti...]`** — tutti gli argomenti passati al comando

Esempio scomposto:

```
/mcp add filesystem npx -y @modelcontextprotocol/server-filesystem /home/daniele
         ─────────  ───────────────────────────────────────────────  ─────────────
         nome        comando + pacchetto npm                         directory esposta
```

- `npx -y` scarica ed esegue un pacchetto npm senza installarlo permanentemente
- `@modelcontextprotocol/server-filesystem` è il pacchetto del server MCP
- `/home/daniele` è l'argomento passato al server (in questo caso la directory a cui dare accesso)

Il risultato nel file `~/.ollama_agent_mcp.json`:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/daniele"],
      "enabled": true
    }
  }
}
```

### Variabili d'ambiente per i server

Alcuni server richiedono API key o token. Puoi passarle nel campo `env` modificando direttamente il file JSON:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_tuotoken"
      },
      "enabled": true
    }
  }
}
```

Oppure esporta la variabile prima di avviare ola:

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN=ghp_tuotoken
ola
```

### Requisiti tecnici

I server MCP basati su `npx` richiedono **Node.js** installato:

```bash
# Verifica
node --version && npx --version

# Installa su Ubuntu/Debian
sudo apt install nodejs npm

# Installa su macOS
brew install node
```

I server basati su `uvx` richiedono **uv** (gestore pacchetti Python):

```bash
# Installa uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

### Catalogo server MCP

Di seguito un elenco completo dei server MCP disponibili, organizzati per categoria. Tutti sono **open source** e gratuiti. Ola li supporta tutti — basta aggiungerli con `/mcp add`.

#### Filesystem e file

| Server | Comando per aggiungerlo | Tool principali | Note |
|---|---|---|---|
| **Filesystem** | `/mcp add filesystem npx -y @modelcontextprotocol/server-filesystem /path/cartella` | `read_file`, `write_file`, `list_directory`, `move_file`, `search_files`, `get_file_info` | Accesso a file e cartelle in una directory specificata. Il path alla fine limita l'accesso solo a quella directory (sicurezza). |
| **Google Drive** | `/mcp add gdrive npx -y @modelcontextprotocol/server-gdrive` | `search_files`, `read_file`, `list_files` | Accesso ai file su Google Drive. Richiede OAuth al primo avvio. |

#### Ricerca web e contenuti

| Server | Comando per aggiungerlo | Tool principali | Note |
|---|---|---|---|
| **Brave Search** | `/mcp add brave npx -y @modelcontextprotocol/server-brave-search` | `brave_web_search`, `brave_local_search` | Ricerca web e locale. Richiede `BRAVE_API_KEY` (gratuita su [brave.com/search/api](https://brave.com/search/api), 2000 query/mese gratis). |
| **Fetch** | `/mcp add fetch npx -y @modelcontextprotocol/server-fetch` | `fetch` | Scarica una pagina web e la converte in testo leggibile (markdown). Utile per far leggere documentazione online al modello. Nessuna API key richiesta. |
| **Tavily** | `/mcp add tavily npx -y tavily-mcp@latest` | `tavily_search`, `tavily_extract` | Ricerca web ottimizzata per AI. Richiede `TAVILY_API_KEY` (1000 query/mese gratis su [tavily.com](https://tavily.com)). |

#### Piattaforme di sviluppo

| Server | Comando per aggiungerlo | Tool principali | Note |
|---|---|---|---|
| **GitHub** | `/mcp add github npx -y @modelcontextprotocol/server-github` | `create_issue`, `list_issues`, `create_pull_request`, `search_repositories`, `get_file_contents`, `create_branch`, `push_files` | Gestione completa di repository GitHub. Richiede `GITHUB_PERSONAL_ACCESS_TOKEN`. |
| **GitLab** | `/mcp add gitlab npx -y @modelcontextprotocol/server-gitlab` | `create_issue`, `list_merge_requests`, `get_file`, `create_merge_request` | Come GitHub ma per GitLab. Richiede `GITLAB_PERSONAL_ACCESS_TOKEN` e `GITLAB_API_URL`. |
| **Git** | `/mcp add git uvx mcp-server-git` | `git_log`, `git_diff`, `git_status`, `git_commit`, `git_branch` | Operazioni git locali su un repository. Alternativa Python (uvx). |

#### Database

| Server | Comando per aggiungerlo | Tool principali | Note |
|---|---|---|---|
| **SQLite** | `/mcp add sqlite npx -y @modelcontextprotocol/server-sqlite /path/database.db` | `read_query`, `write_query`, `list_tables`, `describe_table`, `create_table` | Interroga database SQLite in linguaggio naturale. Il modello scrive le query SQL per te. |
| **PostgreSQL** | `/mcp add postgres npx -y @modelcontextprotocol/server-postgres postgresql://user:pass@localhost/dbname` | `query` | Esegue query SQL su PostgreSQL. Passa la connection string come argomento. |
| **MySQL** | `/mcp add mysql npx -y @benborla29/mcp-server-mysql` | `query`, `list_tables`, `describe_table` | Per database MySQL/MariaDB. Richiede `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` nel env. |
| **Redis** | `/mcp add redis npx -y @modelcontextprotocol/server-redis redis://localhost:6379` | `get`, `set`, `delete`, `list_keys` | Operazioni su database Redis. |
| **MongoDB** | `/mcp add mongodb npx -y @modelcontextprotocol/server-mongodb` | `find`, `insert`, `update`, `aggregate`, `list_collections` | Richiede `MONGODB_URI` nell'env. |

#### Comunicazione e email

| Server | Comando per aggiungerlo | Tool principali | Note |
|---|---|---|---|
| **Gmail** | `/mcp add gmail npx -y @anthropic/mcp-server-gmail` | `search_emails`, `read_email`, `send_email`, `list_labels`, `create_draft` | Accesso a Gmail. Richiede credenziali OAuth Google (file `credentials.json` da Google Cloud Console). |
| **Slack** | `/mcp add slack npx -y @modelcontextprotocol/server-slack` | `send_message`, `list_channels`, `read_messages`, `search_messages`, `reply_to_thread` | Invia e legge messaggi Slack. Richiede `SLACK_BOT_TOKEN` (crea un'app Slack su [api.slack.com](https://api.slack.com)). |
| **Microsoft Teams** | Disponibile come server custom | `send_message`, `list_channels`, `read_messages` | Richiede registrazione app su Azure AD. Configurazione più complessa. |

#### Produttività e documenti

| Server | Comando per aggiungerlo | Tool principali | Note |
|---|---|---|---|
| **Google Calendar** | `/mcp add calendar npx -y @anthropic/mcp-server-google-calendar` | `list_events`, `create_event`, `update_event`, `delete_event` | Gestione calendario Google. Richiede credenziali OAuth. |
| **Google Sheets** | `/mcp add sheets npx -y @anthropic/mcp-server-google-sheets` | `read_sheet`, `write_sheet`, `create_spreadsheet` | Lettura e scrittura fogli Google. Richiede credenziali OAuth. |
| **Notion** | `/mcp add notion npx -y @modelcontextprotocol/server-notion` | `search`, `read_page`, `create_page`, `update_page`, `query_database` | Accesso a workspace Notion. Richiede `NOTION_API_KEY` (crea un'integrazione su [notion.so/my-integrations](https://notion.so/my-integrations)). |
| **Todoist** | `/mcp add todoist npx -y @abhiz123/todoist-mcp-server` | `get_tasks`, `create_task`, `update_task`, `complete_task` | Gestione task Todoist. Richiede `TODOIST_API_TOKEN`. |

#### Infrastruttura e cloud

| Server | Comando per aggiungerlo | Tool principali | Note |
|---|---|---|---|
| **Docker** | `/mcp add docker npx -y @modelcontextprotocol/server-docker` | `list_containers`, `run_container`, `stop_container`, `container_logs`, `list_images` | Gestione container Docker. Richiede accesso al socket Docker. |
| **Kubernetes** | `/mcp add k8s npx -y @modelcontextprotocol/server-kubernetes` | `list_pods`, `get_pod_logs`, `list_services`, `apply_manifest` | Gestione cluster Kubernetes. Usa il kubeconfig locale. |
| **AWS** | `/mcp add aws npx -y @modelcontextprotocol/server-aws` | `s3_list`, `s3_get`, `lambda_invoke`, `cloudwatch_logs` | Servizi AWS. Richiede credenziali AWS configurate (`~/.aws/credentials`). |

#### Browser e automazione

| Server | Comando per aggiungerlo | Tool principali | Note |
|---|---|---|---|
| **Puppeteer** | `/mcp add puppeteer npx -y @modelcontextprotocol/server-puppeteer` | `navigate`, `screenshot`, `click`, `fill`, `evaluate`, `select` | Automazione browser (Chromium). Il modello può navigare siti web, compilare form, fare screenshot. |
| **Playwright** | `/mcp add playwright npx -y @anthropic/mcp-server-playwright` | `navigate`, `screenshot`, `click`, `fill`, `get_text` | Alternativa a Puppeteer di Anthropic, supporta Chrome/Firefox/WebKit. |

#### Memoria e AI

| Server | Comando per aggiungerlo | Tool principali | Note |
|---|---|---|---|
| **Memory** | `/mcp add memory npx -y @modelcontextprotocol/server-memory` | `store_memory`, `retrieve_memory`, `search_memories`, `delete_memory` | Dà al modello una memoria persistente tra sessioni diverse. I dati sono salvati localmente. |
| **Sequential Thinking** | `/mcp add thinking npx -y @modelcontextprotocol/server-sequential-thinking` | `think_step_by_step` | Struttura il ragionamento del modello in passaggi sequenziali. Utile per problemi complessi. |

#### Mappe e geolocalizzazione

| Server | Comando per aggiungerlo | Tool principali | Note |
|---|---|---|---|
| **Google Maps** | `/mcp add maps npx -y @modelcontextprotocol/server-google-maps` | `geocode`, `directions`, `search_places`, `distance_matrix` | Ricerca luoghi, calcolo percorsi. Richiede `GOOGLE_MAPS_API_KEY`. |

#### Monitoraggio e observability

| Server | Comando per aggiungerlo | Tool principali | Note |
|---|---|---|---|
| **Sentry** | `/mcp add sentry npx -y @modelcontextprotocol/server-sentry` | `list_issues`, `get_issue`, `search_events` | Monitoraggio errori da Sentry. Richiede `SENTRY_AUTH_TOKEN`. |

### Configurazione avanzata: più server contemporaneamente

Puoi avere quanti server vuoi attivi contemporaneamente. Ecco un esempio di configurazione completa in `~/.ollama_agent_mcp.json`:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/daniele/Progetti"],
      "enabled": true
    },
    "fetch": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch"],
      "enabled": true
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_tuotoken"
      },
      "enabled": true
    },
    "sqlite": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sqlite", "/home/daniele/dati/app.db"],
      "enabled": true
    },
    "slack": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-slack"],
      "env": {
        "SLACK_BOT_TOKEN": "xoxb-tuotoken"
      },
      "enabled": false
    }
  }
}
```

In questo esempio Slack è configurato ma **disabilitato** (`"enabled": false`). Puoi riabilitarlo con `/mcp enable slack` e poi `/mcp reload`.

### Nota su LibreOffice

Non esiste un server MCP ufficiale per LibreOffice. Tuttavia puoi lavorare con i documenti Office in diversi modi:

- **DOCX/XLSX** → usa il RAG integrato di ola (`/learn file.docx`) — supporta Word ed Excel nativamente
- **ODT/ODS (LibreOffice)** → converti in DOCX/XLSX con `libreoffice --convert-to docx file.odt` e poi usa `/learn`
- **Google Docs/Sheets** → usa i server MCP Google Sheets e Google Drive
- **PDF** → usa il RAG integrato (`/learn file.pdf`)

### Costi e limiti

Il pacchetto `mcp` è **open source Apache 2.0** (Anthropic). Non usa API cloud né richiede chiavi Anthropic: è solo un protocollo JSON-RPC su stdio. I server MCP girano in locale come subprocess, senza quote né limiti. I costi LLM restano quelli del provider configurato (Ollama, OpenAI, ecc.).

I server che accedono a servizi cloud (GitHub, Slack, Gmail, ecc.) richiedono le rispettive API key o token OAuth, ma il protocollo MCP in sé è sempre gratuito e senza limiti.

### Robustezza

- Un server MCP che non parte o va in errore **non blocca ola**: viene mostrato come errore in `/mcp list`, gli altri server continuano a funzionare
- Il pacchetto `mcp` è incluso nelle dipendenze — installato automaticamente da `install.sh`/`install.bat`
- MCP è **completamente opzionale**: se non hai config, ola funziona identico alle versioni precedenti
- Ogni server gira come **processo separato**: se uno crasha, gli altri continuano normalmente

---

## Ricerca web (`/web`)

Ola può cercare informazioni su internet quando necessario — utile per documentazione aggiornata, versioni recenti di librerie, eventi attuali, o qualsiasi cosa non presente nei dati di addestramento del modello. La funzione è **opzionale** e **disattivata di default**.

### Come funziona

Quando abiliti la ricerca web, ola espone al modello due nuovi tool:

| Tool | Cosa fa |
|---|---|
| `web_search(query)` | Cerca sul web e restituisce i top 5 risultati (titolo, URL, snippet) |
| `web_fetch(url)` | Scarica una pagina e la converte in testo markdown leggibile |

Il modello li usa in sequenza: prima `web_search` per trovare le pagine rilevanti, poi `web_fetch` su 1-2 risultati migliori per leggerne il contenuto completo. I risultati vengono citati nella risposta con l'URL.

Quando il web è **disattivato**, i tool non vengono nemmeno esposti al modello — nessuna distrazione, nessun rischio di chiamate involontarie.

### Comandi

```bash
/web                                 # mostra stato corrente
/web on                              # attiva la ricerca web
/web off                             # disattiva la ricerca web
/web provider duckduckgo             # cambia motore (default)
/web provider brave                  # usa Brave Search (serve API key)
/web provider tavily                 # usa Tavily (serve API key)
```

La scelta è **persistente** (salvata in `~/.ollama_agent_prefs.json`) e visibile in `/settings` come `web access: on (duckduckgo)`.

### I tre provider supportati

| Provider | API key | Qualità | Quota gratuita | Note |
|---|---|---|---|---|
| **DuckDuckGo** (default) | ❌ Nessuna | Media | Illimitata (rate-limited) | Zero setup, funziona subito. Installato da `install.sh`/`install.bat` |
| **Brave Search** | ✅ `BRAVE_API_KEY` | Alta | 2000 query/mese | Indice proprio di 50+ miliardi di pagine. Key gratuita su [brave.com/search/api](https://brave.com/search/api) |
| **Tavily** | ✅ `TAVILY_API_KEY` | Ottima (AI-optimized) | 1000 query/mese | Ottimizzato per LLM: restituisce già contenuti sintetici. Key gratuita su [tavily.com](https://tavily.com) |

### Configurare una API key

Per usare Brave o Tavily, aggiungi la key al file `.env`:

```env
BRAVE_API_KEY=BSA...
TAVILY_API_KEY=tvly-...
```

Oppure esportala come variabile d'ambiente prima di avviare ola:

```bash
export BRAVE_API_KEY=BSA...
ola
```

Se cambi provider con `/web provider brave` ma la key non è configurata, ola ti avvisa con un messaggio in giallo.

### Esempio pratico

```
> /web on
  Web access: ON (provider: duckduckgo) — saved

> quali novità ci sono nella versione 3.13 di Python?
  · web_search
  · web_fetch
  La versione 3.13 di Python, rilasciata il 7 ottobre 2024, include
  diverse novità importanti [python.org/downloads/release/python-3130/]:

  1. **JIT experimental**: un nuovo compilatore just-in-time...
  2. **GIL opzionale**: supporto sperimentale per disabilitare il GIL...
  ...
```

### Dipendenze

Le dipendenze vengono installate automaticamente da `install.sh`/`install.bat`:

- **httpx** — client HTTP per fetch e chiamate API
- **ddgs** — client DuckDuckGo (no API key)
- **markdownify** — conversione HTML → markdown per `web_fetch`

Se hai installato a mano:

```bash
pip install httpx ddgs markdownify
```

### Privacy e limiti

- **DuckDuckGo**: le query vanno a DuckDuckGo, che non traccia gli utenti. Rate limit può bloccarti temporaneamente se usi molto.
- **Brave**: le query passano dai server Brave (privacy-focused per policy). La API key identifica te, non il modello.
- **Tavily**: commerciale ma con privacy policy standard. API key identificativa.
- **`web_fetch`**: fa richieste HTTP dirette ai siti con user agent `OlaAgent`. Alcuni siti possono bloccarlo (serve un server MCP dedicato in quei casi).

### Quando usarla e quando no

| Scenario | Web mode |
|---|---|
| Domande sulla tua base di codice | ❌ NO — usa RAG (`/learn`) |
| Domande su librerie aggiornate, versioni recenti | ✅ SÌ |
| Ricerca documentazione ufficiale di un framework | ✅ SÌ |
| Eventi attuali, notizie | ✅ SÌ |
| Lettura di una pagina specifica che conosci già | ✅ SÌ (`web_fetch`) |
| Conversazioni veloci e chiacchiere | ❌ NO (aumenta token inutilmente) |

Tenere la ricerca web **sempre attiva** è sconsigliato: il modello potrebbe usarla anche quando non serve, sprecando token. Meglio attivarla quando serve e disattivarla dopo.

---

## Produttività: `/compact`, `/commit`, `/undo`, `/costs`

Quattro comandi pensati per le sessioni lunghe di lavoro reale.

### `/compact` — riduci i token di contesto

Quando la conversazione diventa lunga, ogni nuovo messaggio paga in token tutto lo storico precedente. `/compact` chiede al modello corrente di riassumere la conversazione in un blocco breve (≤350 parole) e sostituisce la cronologia col riassunto, preservando il system prompt e il contesto progetto (AGENT.md).

```
> /compact
  Riassumo la conversazione...
  ✓ Conversazione compattata: 42 → 3 messaggi  (1247 caratteri di riassunto)
```

Da usare prima di affrontare un nuovo task correlato, o quando ola inizia a "dimenticare" i primi scambi. La conversazione successiva al `/compact` riparte leggera ma con memoria dell'essenziale.

### `/commit` — commit con messaggio generato dall'LLM

Flusso completo: controlla `git status` / `git diff --cached`, se nulla è in staging ti propone `git add -A`, manda diff e log recente al modello, ti mostra il messaggio proposto e chiede conferma.

```
> /commit
  Generazione messaggio di commit...
  ┌─ Messaggio di commit proposto ──────────────────────────┐
  │ feat(web): add /web command with 3 provider support    │
  │                                                         │
  │ - DuckDuckGo default (no API key)                       │
  │ - Brave and Tavily opt-in with env keys                 │
  │ - Tools exposed only when /web on                       │
  └─────────────────────────────────────────────────────────┘
  Commit? [Y/n/e=edit]
```

Premendo `e` puoi riscrivere il messaggio a mano prima di committare. Il modello imita lo stile dei commit recenti (`git log --oneline -n 10`), quindi la lingua e la forma si allineano al repo.

### `/undo` — annulla l'ultima modifica dell'agent

Ogni `write_file` e `edit_file` fatto dall'agent salva prima un backup in `~/.ollama_agent_backups/`. `/undo` ripristina lo stato precedente all'ultima operazione (e può essere chiamato più volte per tornare indietro di più passi).

```
> scrivi config.py con i nuovi parametri
  · write_file
> /undo
  ✓ Ripristinato (write_file): /home/daniele/progetto/config.py
    (3 operazioni ancora annullabili)
```

Se il file è stato creato ex-novo dall'operazione, `/undo` lo elimina. Lo stack è per sessione: aprendo una nuova istanza di ola si riparte vuoti. Sono conservate fino a 100 operazioni per sessione.

### `/costs` — stima costi per provider/modello

Tiene traccia dei token per ogni coppia `provider/modello` usata nella sessione e nella settimana corrente, e li moltiplica per i prezzi list (USD per 1M token).

```
> /costs
  ┌─ Costi stimati — sessione ──────────────────────────────────┐
  │ provider/model                input  output   cost  /1M (in/out)
  │ openrouter/claude-3.5-sonnet 12,450   3,890 $0.096  $3.00 / $15.00
  │ ollama/qwen2.5-coder:7b       8,200   2,100 $0.0000 $0.00 / $0.00
  │ totale sessione              20,650   5,990 $0.096
  └─────────────────────────────────────────────────────────────┘
```

I modelli Ollama locali sono segnati a `$0.00`. I prezzi cloud sono conservativi ma indicativi — puoi sovrascriverli creando `~/.ollama_agent_prices.json` con la stessa struttura di `PRICES` in `ollama_agent/costs.py`.

Esempio per aggiornare il prezzo di un singolo modello:

```json
{
  "openrouter": {
    "anthropic/claude-3.5-sonnet": [3.0, 15.0],
    "deepseek/deepseek-chat": [0.14, 0.28]
  }
}
```

I totali settimanali si azzerano automaticamente al cambio di settimana ISO.

---

## Strumenti disponibili

Il modello può usare autonomamente questi strumenti. Quelli che modificano il sistema richiedono consenso (in modalità manual, il default):

| Strumento | Descrizione | Consenso |
|---|---|---|
| `read_file` | Legge un file con i numeri di riga | No |
| `list_dir` | Elenca il contenuto di una directory | No |
| `grep` | Cerca con regex nei file | No |
| `find_files` | Trova file tramite pattern glob | No |
| `search_knowledge` | Cerca nella knowledge base RAG | No |
| `web_search` | Cerca sul web (richiede `/web on`) | No |
| `web_fetch` | Scarica e legge una pagina web (richiede `/web on`) | No |
| `bash` | Esegue comandi shell | **Sì** |
| `write_file` | Crea o sovrascrive un file | **Sì** (write preview) |
| `edit_file` | Sostituisce una stringa esatta in un file | **Sì** (diff preview) |

Oltre agli strumenti, Ollama Agent riconosce automaticamente i **percorsi di immagini** nel messaggio utente (png, jpg, jpeg, gif, webp, bmp) e li invia al modello come contenuto multimodale — vedi [Supporto immagini e OCR](#supporto-immagini-e-ocr). Per usare questa funzione serve un modello con capacità vision.

---

## Comandi Ollama utili

Riferimento rapido ai comandi `ollama` più usati insieme a Ollama Agent.

### Modelli

```bash
# Scarica un modello
ollama pull qwen2.5-coder:7b
ollama pull llama3.1:8b
ollama pull granite-embedding:30m   # modello embedding per il RAG (scaricato automaticamente)

# Lista modelli installati
ollama list

# Rimuovi un modello
ollama rm qwen2.5-coder:7b

# Mostra i modelli in esecuzione e il loro uso di memoria
ollama ps

# Dettagli e parametri di un modello
ollama show qwen2.5-coder:7b
```

### Modelli cloud Ollama

I modelli con il tag `:cloud` girano su infrastruttura Ollama — non occupano spazio sul disco e non richiedono GPU.

```bash
ollama pull deepseek-v3.1:671b-cloud
ollama pull kimi-k2.5:cloud
```

> I modelli cloud hanno un limite di utilizzo mensile gratuito. Verifica i tuoi consumi su [ollama.com](https://ollama.com).

### Servizio

```bash
# Avvia il server Ollama (di solito parte automaticamente)
ollama serve

# Verifica che Ollama stia girando
curl http://localhost:11434
```

### Velocità e hardware

```bash
# Verifica se Ollama sta usando la GPU
ollama ps

# Esegui una chat rapida da terminale (utile per testare un modello)
ollama run qwen2.5-coder:7b "ciao"

# Esci dalla chat interattiva di Ollama
/bye
```

### Modelli consigliati per Ollama Agent

| Modello | Dimensione | Tool calling | Ideale per |
|---|---|---|---|
| `qwen2.5-coder:7b` | ~5 GB | Sì | Coding, veloce |
| `qwen2.5-coder:14b` | ~9 GB | Sì | Coding, più preciso |
| `llama3.1:8b` | ~5 GB | Sì | Uso generale |
| `llama3.2:3b` | ~2 GB | Sì | Macchine con poca RAM |
| `mistral-nemo` | ~7 GB | Sì | Buon equilibrio |
| `deepseek-v3.1:671b-cloud` | — | Sì | Cloud, molto capace |
| `kimi-k2.5:cloud` | — | Sì | Cloud, coding avanzato |
| `granite-embedding:30m` | 60 MB | — | Solo RAG/embedding (auto) |

> **Nota:** i modelli Qwen3 (es. `qwen3:8b`) hanno una modalità di ragionamento interno (`<think>`) che può rallentare molto le risposte su CPU. Ollama Agent la gestisce automaticamente mostrando `reasoning... (N tok)` nello spinner.

---

## Opzioni CLI

```
ola [OPTIONS] [PROMPT]

Options:
  -p, --provider [ollama|openai|groq|openrouter]
                          Provider LLM  [default: ollama]
  -m, --model TEXT        Nome del modello (sovrascrive il default del provider)
  --base-url TEXT         URL base API personalizzato
  --api-key TEXT          API key (sovrascrive la variabile d'ambiente)
  --help                  Mostra questo messaggio ed esce
```

---

## Struttura del progetto

```
ollama-agent/
├── pyproject.toml              # configurazione pacchetto, entry point `ola`
├── .env.example                # template variabili d'ambiente
├── install.sh                  # installer Linux / macOS
├── install.bat                 # installer Windows
├── dist/
│   └── ollama_agent-0.6.0-py3-none-any.whl   # wheel precompilato
└── ollama_agent/
    ├── main.py                 # CLI, sessione interattiva, comandi slash
    ├── agent.py                # loop agente, streaming, spinner, usage
    ├── config.py               # configurazione multi-provider
    ├── tools/
    │   ├── bash.py             # esecuzione comandi shell
    │   ├── files.py            # read / write / edit / list
    │   └── search.py           # grep e find_files
    └── rag/
        ├── chunker.py          # suddivisione file in chunk
        ├── store.py            # vector store su disco (JSON + coseno)
        └── retriever.py        # embedding, indicizzazione e ricerca
```
