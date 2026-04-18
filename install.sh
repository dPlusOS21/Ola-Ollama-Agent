#!/usr/bin/env bash
# Ollama Agent — installer for Linux / macOS
set -e

BOLD="\033[1m"
CYAN="\033[1;36m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
DIM="\033[2m"
RESET="\033[0m"

echo -e "${CYAN}"
echo "  ╔═══════════════════════════════════════╗"
echo "  ║      Ollama Agent — Installer         ║"
echo "  ╚═══════════════════════════════════════╝"
echo -e "${RESET}"

# ── Python check ────────────────────────────────────────────────────────────
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" -c "import sys; print(sys.version_info[:2] >= (3,10))" 2>/dev/null)
        if [ "$ver" = "True" ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo -e "${RED}✗ Python 3.10+ not found.${RESET}"
    echo "  Install it from https://www.python.org/downloads/"
    exit 1
fi
echo -e "${GREEN}✓${RESET} Python: $($PYTHON --version)"

# ── pip check ────────────────────────────────────────────────────────────────
if ! $PYTHON -m pip --version &>/dev/null; then
    echo -e "${RED}✗ pip not found. Install pip first.${RESET}"
    exit 1
fi

# ── Ollama check / install / update ─────────────────────────────────────────

# Get the latest Ollama version from GitHub API (best-effort)
get_latest_ollama_version() {
    if command -v curl &>/dev/null; then
        curl -fsSL --connect-timeout 5 --max-time 10 \
            "https://api.github.com/repos/ollama/ollama/releases/latest" 2>/dev/null \
            | $PYTHON -c "import sys,json; print(json.load(sys.stdin).get('tag_name',''))" 2>/dev/null
    elif command -v wget &>/dev/null; then
        wget -qO- --timeout=10 \
            "https://api.github.com/repos/ollama/ollama/releases/latest" 2>/dev/null \
            | $PYTHON -c "import sys,json; print(json.load(sys.stdin).get('tag_name',''))" 2>/dev/null
    fi
}

# Normalize version string: strip leading "v", keep digits and dots
normalize_version() {
    echo "$1" | sed 's/^v//' | grep -oE '[0-9]+\.[0-9]+[0-9.]*'
}

# Compare two version strings: returns 0 if $1 < $2
version_lt() {
    [ "$1" = "$2" ] && return 1
    local lowest
    lowest=$(printf '%s\n%s\n' "$1" "$2" | sort -V | head -n1)
    [ "$lowest" = "$1" ]
}

install_ollama() {
    echo ""
    echo -e "${BOLD}Installing Ollama...${RESET}"
    if curl -fsSL https://ollama.com/install.sh | sh; then
        echo -e "${GREEN}✓${RESET} Ollama installed successfully"
        return 0
    else
        echo -e "${RED}✗ Ollama automatic installation failed.${RESET}"
        echo "  Install it manually from: https://ollama.com/download"
        return 1
    fi
}

if command -v ollama &>/dev/null; then
    # Ollama is installed — check version and offer update
    CURRENT_RAW=$(ollama --version 2>/dev/null || echo "")
    # ollama --version output varies: "ollama version is 0.6.2" or "0.6.2"
    CURRENT_VER=$(normalize_version "$CURRENT_RAW")

    if [ -n "$CURRENT_VER" ]; then
        echo -e "${GREEN}✓${RESET} Ollama: v${CURRENT_VER}"
    else
        echo -e "${GREEN}✓${RESET} Ollama: installed ${DIM}(version unknown)${RESET}"
    fi

    # Check for updates
    echo -e "${DIM}  Checking for updates...${RESET}"
    LATEST_RAW=$(get_latest_ollama_version)
    LATEST_VER=$(normalize_version "$LATEST_RAW")

    if [ -n "$LATEST_VER" ] && [ -n "$CURRENT_VER" ]; then
        if version_lt "$CURRENT_VER" "$LATEST_VER"; then
            echo ""
            echo -e "${YELLOW}⬆${RESET}  A newer version of Ollama is available: ${BOLD}v${LATEST_VER}${RESET} ${DIM}(current: v${CURRENT_VER})${RESET}"
            echo ""
            read -rp "  Do you want to update Ollama? [y/N] " answer
            case "$answer" in
                [yY]|[yY][eE][sS])
                    install_ollama
                    ;;
                *)
                    echo -e "${DIM}  Skipping Ollama update.${RESET}"
                    ;;
            esac
        else
            echo -e "${DIM}  Ollama is up to date.${RESET}"
        fi
    elif [ -z "$LATEST_VER" ]; then
        echo -e "${DIM}  Could not check for updates (no network?). Skipping.${RESET}"
    fi
else
    # Ollama is not installed — offer to install
    echo -e "${YELLOW}⚠${RESET}  Ollama is not installed."
    echo "  Ollama is required to use local and cloud models (default provider)."
    echo ""
    read -rp "  Do you want to install Ollama now? [Y/n] " answer
    case "$answer" in
        [nN]|[nN][oO])
            echo -e "${DIM}  Skipping Ollama installation.${RESET}"
            echo "  You can install it later from: https://ollama.com/download"
            echo "  Note: Ollama Agent will not work without Ollama unless you use"
            echo "  an alternative provider (openai, groq, openrouter)."
            ;;
        *)
            install_ollama
            ;;
    esac
fi

# ── Install Ollama Agent ────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Installing Ollama Agent...${RESET}"

# Determine install source: directory containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Prefer pre-built wheel if present (faster, no build tools needed)
WHEEL=$(ls "$SCRIPT_DIR"/dist/ollama_agent-*.whl 2>/dev/null | head -1)
if [ -n "$WHEEL" ]; then
    $PYTHON -m pip install --quiet "$WHEEL"
else
    $PYTHON -m pip install --quiet "$SCRIPT_DIR"
fi

echo -e "${GREEN}✓${RESET} Ollama Agent installed"

# ── Voice (microphone) dependencies ──────────────────────────────────────────
echo ""
echo -e "${BOLD}Installing voice input dependencies (microfono + Whisper)...${RESET}"

# On Linux we need the PortAudio shared library for sounddevice to work.
if [ -f /etc/debian_version ]; then
    if ! dpkg -s libportaudio2 &>/dev/null; then
        echo -e "${DIM}  Installing libportaudio2 (richiede sudo)...${RESET}"
        sudo apt-get update -qq && sudo apt-get install -y -qq libportaudio2 \
            && echo -e "${GREEN}✓${RESET} libportaudio2 installed" \
            || echo -e "${YELLOW}⚠${RESET}  libportaudio2 non installato — /voice potrebbe non funzionare"
    else
        echo -e "${GREEN}✓${RESET} libportaudio2 già presente"
    fi
elif [ -f /etc/redhat-release ]; then
    if ! rpm -q portaudio &>/dev/null; then
        echo -e "${DIM}  Installing portaudio (richiede sudo)...${RESET}"
        sudo dnf install -y -q portaudio \
            && echo -e "${GREEN}✓${RESET} portaudio installed" \
            || echo -e "${YELLOW}⚠${RESET}  portaudio non installato"
    fi
fi

$PYTHON -m pip install --quiet faster-whisper sounddevice numpy \
    && echo -e "${GREEN}✓${RESET} Voice deps installed (faster-whisper, sounddevice, numpy)" \
    || echo -e "${YELLOW}⚠${RESET}  Voice deps not installed — /voice non sarà disponibile"

# ── MCP (Model Context Protocol) ────────────────────────────────────────────
$PYTHON -m pip install --quiet mcp \
    && echo -e "${GREEN}✓${RESET} MCP client installed (pacchetto 'mcp')" \
    || echo -e "${YELLOW}⚠${RESET}  MCP non installato — /mcp non sarà disponibile"

# ── Web search dependencies ─────────────────────────────────────────────────
$PYTHON -m pip install --quiet httpx ddgs markdownify \
    && echo -e "${GREEN}✓${RESET} Web search deps installed (httpx, ddgs, markdownify)" \
    || echo -e "${YELLOW}⚠${RESET}  Web deps non installati — /web non sarà disponibile"

# ── Verify ola is reachable ──────────────────────────────────────────────────
if ! command -v ola &>/dev/null; then
    # pip may install to ~/.local/bin which might not be in PATH
    LOCAL_BIN="$HOME/.local/bin"
    if [ -f "$LOCAL_BIN/ola" ]; then
        echo ""
        echo -e "${YELLOW}⚠${RESET}  The 'ola' command was installed to ${LOCAL_BIN}"
        echo "  Add it to your PATH by running:"
        echo ""
        echo -e "    ${BOLD}echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc && source ~/.bashrc${RESET}"
        echo ""
        echo "  (replace ~/.bashrc with ~/.zshrc if you use zsh)"
    fi
else
    echo -e "${GREEN}✓${RESET} Command 'ola' is ready"
fi

# ── .env setup ───────────────────────────────────────────────────────────────
if [ ! -f "$SCRIPT_DIR/.env" ] && [ -f "$SCRIPT_DIR/.env.example" ]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo -e "${GREEN}✓${RESET} Created .env from .env.example"
    echo "  Edit .env to add API keys for OpenAI, Groq, or OpenRouter (optional)"
fi

# ── Pull embedding model ───────────────────────────────────────────────────
if command -v ollama &>/dev/null; then
    echo ""
    echo -e "${BOLD}Pulling embedding model (granite-embedding:30m)...${RESET}"
    if ollama pull granite-embedding:30m 2>/dev/null; then
        echo -e "${GREEN}✓${RESET} Embedding model granite-embedding:30m ready"
    else
        echo -e "${YELLOW}⚠${RESET}  Could not pull embedding model now (no network?)."
        echo "  It will be downloaded automatically on first /learn use."
    fi
fi

# ── Ollama parallel config ─────────────────────────────────────────────────
if command -v ollama &>/dev/null; then
    DROPIN_DIR="/etc/systemd/system/ollama.service.d"
    DROPIN_FILE="$DROPIN_DIR/parallel.conf"
    if [ ! -f "$DROPIN_FILE" ] && command -v systemctl &>/dev/null; then
        echo ""
        echo -e "${DIM}  Configuring Ollama for parallel embedding (OLLAMA_NUM_PARALLEL=4)...${RESET}"
        sudo mkdir -p "$DROPIN_DIR" 2>/dev/null && \
        printf '[Service]\nEnvironment="OLLAMA_NUM_PARALLEL=4"\nEnvironment="OLLAMA_MAX_LOADED_MODELS=2"\n' | \
            sudo tee "$DROPIN_FILE" >/dev/null 2>/dev/null && \
        sudo systemctl daemon-reload 2>/dev/null && \
        sudo systemctl restart ollama 2>/dev/null && \
        echo -e "${GREEN}✓${RESET} Ollama parallel config installed" || \
        echo -e "${DIM}  Skipped parallel config (no sudo or no systemd).${RESET}"
    fi
fi

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}${BOLD}Done!${RESET} Start Ollama Agent with:"
echo ""
echo -e "    ${BOLD}ola${RESET}                          # interactive mode (Ollama default)"
echo -e "    ${BOLD}ola -m qwen2.5-coder:7b${RESET}     # specific local model"
echo -e "    ${BOLD}ola -p openai${RESET}                # OpenAI provider"
echo ""
