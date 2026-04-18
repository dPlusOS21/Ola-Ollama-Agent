@echo off
setlocal EnableDelayedExpansion

echo.
echo   +------------------------------------------+
echo   ^|     Ollama Agent -- Installer            ^|
echo   +------------------------------------------+
echo.

:: ── Python check ────────────────────────────────────────────────────────────
set PYTHON=
for %%c in (python python3) do (
    if "!PYTHON!"=="" (
        %%c -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
        if !errorlevel! == 0 (
            set PYTHON=%%c
        )
    )
)

if "!PYTHON!"=="" (
    echo [ERRORE] Python 3.10+ non trovato.
    echo Scaricalo da: https://www.python.org/downloads/
    echo Assicurati di spuntare "Add Python to PATH" durante l'installazione.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('!PYTHON! --version') do echo [OK] %%v

:: ── pip check ────────────────────────────────────────────────────────────────
!PYTHON! -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERRORE] pip non trovato.
    pause
    exit /b 1
)

:: ── Ollama check / install / update ─────────────────────────────────────────
where ollama >nul 2>&1
if errorlevel 1 (
    echo [AVVISO] Ollama non e' installato.
    echo          Ollama e' necessario per usare i modelli locali e cloud ^(provider predefinito^).
    echo.
    set /p INSTALL_OLLAMA="  Vuoi installare Ollama ora? [S/n] "
    if /i "!INSTALL_OLLAMA!"=="n" (
        echo          Installazione di Ollama saltata.
        echo          Puoi installarlo manualmente da: https://ollama.com/download
        echo          Nota: Ollama Agent non funzionera' senza Ollama a meno che tu non usi
        echo          un provider alternativo ^(openai, groq, openrouter^).
    ) else if /i "!INSTALL_OLLAMA!"=="no" (
        echo          Installazione di Ollama saltata.
    ) else (
        echo.
        echo Scaricamento di Ollama in corso...
        set "OLLAMA_INSTALLER=%TEMP%\OllamaSetup.exe"

        :: Try PowerShell download
        powershell -NoProfile -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('https://ollama.com/download/OllamaSetup.exe', '%TEMP%\OllamaSetup.exe') } catch { exit 1 }" >nul 2>&1
        if exist "!OLLAMA_INSTALLER!" (
            echo Avvio dell'installer di Ollama...
            echo ^(segui le istruzioni nella finestra che si apre^)
            start /wait "" "!OLLAMA_INSTALLER!"
            del "!OLLAMA_INSTALLER!" >nul 2>&1

            :: Verify installation
            where ollama >nul 2>&1
            if errorlevel 1 (
                echo [AVVISO] Ollama non risulta nel PATH. Potrebbe essere necessario
                echo          riavviare il terminale dopo l'installazione.
            ) else (
                echo [OK] Ollama installato con successo
            )
        ) else (
            echo [ERRORE] Download di Ollama fallito.
            echo          Installalo manualmente da: https://ollama.com/download
        )
    )
) else (
    :: Ollama is installed — get current version
    set CURRENT_VER=
    for /f "tokens=*" %%v in ('ollama --version 2^>nul') do set "CURRENT_VER_RAW=%%v"

    :: Extract version number (handle "ollama version is X.Y.Z" and plain "X.Y.Z")
    !PYTHON! -c "import re,sys; m=re.search(r'(\d+\.\d+[\d.]*)', r'!CURRENT_VER_RAW!'); print(m.group(1) if m else '')" > "%TEMP%\ola_curver.txt" 2>nul
    set /p CURRENT_VER=<"%TEMP%\ola_curver.txt"
    del "%TEMP%\ola_curver.txt" >nul 2>&1

    if "!CURRENT_VER!"=="" (
        echo [OK] Ollama installato ^(versione sconosciuta^)
    ) else (
        echo [OK] Ollama: v!CURRENT_VER!
    )

    :: Check for updates via GitHub API
    echo          Controllo aggiornamenti...
    set LATEST_VER=
    !PYTHON! -c "import urllib.request,json,re,sys; r=urllib.request.urlopen('https://api.github.com/repos/ollama/ollama/releases/latest',timeout=10); d=json.loads(r.read()); m=re.search(r'(\d+\.\d+[\d.]*)',d.get('tag_name','')); print(m.group(1) if m else '')" > "%TEMP%\ola_latver.txt" 2>nul
    set /p LATEST_VER=<"%TEMP%\ola_latver.txt"
    del "%TEMP%\ola_latver.txt" >nul 2>&1

    if "!LATEST_VER!"=="" (
        echo          Impossibile verificare aggiornamenti. Salto il controllo.
    ) else if "!CURRENT_VER!"=="" (
        echo          Impossibile confrontare le versioni. Salto il controllo.
    ) else (
        :: Compare versions using Python
        !PYTHON! -c "from packaging.version import Version; exit(0 if Version('!CURRENT_VER!') < Version('!LATEST_VER!') else 1)" >nul 2>&1
        if !errorlevel! == 0 (
            echo.
            echo [AGGIORNAMENTO] Nuova versione di Ollama disponibile: v!LATEST_VER! ^(attuale: v!CURRENT_VER!^)
            echo.
            set /p UPDATE_OLLAMA="  Vuoi aggiornare Ollama? [s/N] "
            if /i "!UPDATE_OLLAMA!"=="s" (
                echo.
                echo Scaricamento di Ollama v!LATEST_VER! in corso...
                set "OLLAMA_INSTALLER=%TEMP%\OllamaSetup.exe"
                powershell -NoProfile -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('https://ollama.com/download/OllamaSetup.exe', '%TEMP%\OllamaSetup.exe') } catch { exit 1 }" >nul 2>&1
                if exist "!OLLAMA_INSTALLER!" (
                    echo Avvio dell'installer di Ollama...
                    start /wait "" "!OLLAMA_INSTALLER!"
                    del "!OLLAMA_INSTALLER!" >nul 2>&1
                    echo [OK] Ollama aggiornato
                ) else (
                    echo [ERRORE] Download fallito. Aggiorna manualmente da: https://ollama.com/download
                )
            ) else if /i "!UPDATE_OLLAMA!"=="si" (
                echo.
                echo Scaricamento di Ollama v!LATEST_VER! in corso...
                set "OLLAMA_INSTALLER=%TEMP%\OllamaSetup.exe"
                powershell -NoProfile -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('https://ollama.com/download/OllamaSetup.exe', '%TEMP%\OllamaSetup.exe') } catch { exit 1 }" >nul 2>&1
                if exist "!OLLAMA_INSTALLER!" (
                    echo Avvio dell'installer di Ollama...
                    start /wait "" "!OLLAMA_INSTALLER!"
                    del "!OLLAMA_INSTALLER!" >nul 2>&1
                    echo [OK] Ollama aggiornato
                ) else (
                    echo [ERRORE] Download fallito. Aggiorna manualmente da: https://ollama.com/download
                )
            ) else (
                echo          Aggiornamento di Ollama saltato.
            )
        ) else (
            echo          Ollama e' aggiornato.
        )
    )
)

:: ── Install Ollama Agent ────────────────────────────────────────────────────
echo.
echo Installazione di Ollama Agent...
set SCRIPT_DIR=%~dp0

:: Prefer pre-built wheel if present
set WHEEL=
for %%f in ("%SCRIPT_DIR%dist\ollama_agent-*.whl") do set WHEEL=%%f

if not "!WHEEL!"=="" (
    !PYTHON! -m pip install --quiet "!WHEEL!"
) else (
    !PYTHON! -m pip install --quiet "%SCRIPT_DIR%"
)
if errorlevel 1 (
    echo [ERRORE] Installazione fallita.
    pause
    exit /b 1
)
echo [OK] Ollama Agent installato

:: ── Voice (microphone) dependencies ──────────────────────────────────────────
echo.
echo Installazione dipendenze input vocale ^(microfono + Whisper^)...
!PYTHON! -m pip install --quiet faster-whisper sounddevice numpy
if errorlevel 1 (
    echo [AVVISO] Dipendenze vocali non installate — /voice non sara' disponibile
) else (
    echo [OK] Dipendenze vocali installate ^(faster-whisper, sounddevice, numpy^)
)

:: ── MCP (Model Context Protocol) ─────────────────────────────────────────────
!PYTHON! -m pip install --quiet mcp
if errorlevel 1 (
    echo [AVVISO] MCP non installato — /mcp non sara' disponibile
) else (
    echo [OK] MCP client installato ^(pacchetto 'mcp'^)
)

:: ── .env setup ───────────────────────────────────────────────────────────────
if not exist "%SCRIPT_DIR%.env" (
    if exist "%SCRIPT_DIR%.env.example" (
        copy "%SCRIPT_DIR%.env.example" "%SCRIPT_DIR%.env" >nul
        echo [OK] Creato .env da .env.example
        echo      Modifica .env per aggiungere API key (OpenAI, Groq, OpenRouter)
    )
)

:: ── Pull embedding model ───────────────────────────────────────────────────
where ollama >nul 2>&1
if not errorlevel 1 (
    echo.
    echo Scaricamento modello embedding ^(granite-embedding:30m^)...
    ollama pull granite-embedding:30m >nul 2>&1
    if not errorlevel 1 (
        echo [OK] Modello embedding granite-embedding:30m pronto
    ) else (
        echo [AVVISO] Impossibile scaricare il modello embedding ora.
        echo          Verra' scaricato automaticamente al primo utilizzo di /learn.
    )
)

:: ── Done ─────────────────────────────────────────────────────────────────────
echo.
echo Installazione completata! Avvia Ollama Agent con:
echo.
echo   ola                           (modalita' interattiva, Ollama predefinito)
echo   ola -m qwen2.5-coder:7b       (modello locale specifico)
echo   ola -p openai                  (provider OpenAI)
echo.
pause
