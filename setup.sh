#!/usr/bin/env bash
# CodeSentinel AI — one-shot environment installer.
# Idempotent: safe to re-run.
set -euo pipefail

RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[1;33m'; BLU='\033[0;34m'; NC='\033[0m'
say()   { printf "${BLU}[setup]${NC} %s\n" "$*"; }
ok()    { printf "${GRN}[ ok ]${NC} %s\n" "$*"; }
warn()  { printf "${YLW}[warn]${NC} %s\n" "$*"; }
fail()  { printf "${RED}[fail]${NC} %s\n" "$*"; exit 1; }

cd "$(dirname "$0")"

# ---------- 1. Platform check ----------
say "Checking platform..."
OS="$(uname -s)"; ARCH="$(uname -m)"
[[ "$OS" == "Darwin" ]] || warn "Not macOS ($OS) — script optimised for Apple Silicon Macs. Continuing."
[[ "$ARCH" == "arm64" ]] || warn "Not arm64 ($ARCH) — Metal acceleration may be unavailable."
ok "Platform: $OS $ARCH"

# ---------- 2. Homebrew ----------
say "Checking Homebrew..."
command -v brew >/dev/null 2>&1 || fail "Homebrew not installed. See https://brew.sh"
ok "Homebrew at $(command -v brew)"

# ---------- 3. Python 3.12 ----------
say "Checking python@3.12..."
if ! command -v python3.12 >/dev/null 2>&1; then
    say "Installing python@3.12 via brew..."
    brew install python@3.12
fi
PY312=$(command -v python3.12)
ok "python3.12 at $PY312 ($($PY312 --version))"

# ---------- 4. Ollama ----------
say "Checking Ollama..."
if ! command -v ollama >/dev/null 2>&1; then
    say "Installing Ollama via brew..."
    if ! brew install --cask ollama-app 2>/dev/null; then
        brew install ollama
    fi
fi
OLLAMA=$(command -v ollama || true)
[[ -n "$OLLAMA" ]] || fail "Ollama install failed."
ok "Ollama at $OLLAMA"

# ---------- 5. Start Ollama daemon ----------
say "Ensuring Ollama daemon is running..."
if ! curl -sf http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
    # Prefer the GUI app if present (cask install), else background headless serve
    if [[ -d "/Applications/Ollama.app" ]]; then
        open -a Ollama >/dev/null 2>&1 || true
    else
        nohup ollama serve >/tmp/ollama.log 2>&1 &
    fi
    say "Waiting for Ollama daemon..."
    for i in {1..30}; do
        if curl -sf http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
            break
        fi
        sleep 1
    done
fi
curl -sf http://127.0.0.1:11434/api/version >/dev/null 2>&1 || fail "Ollama daemon not reachable on 127.0.0.1:11434"
ok "Ollama daemon reachable"

# ---------- 6. Pull primary model ----------
PRIMARY_MODEL="${OLLAMA_MODEL:-qwen2.5-coder:7b-instruct-q4_K_M}"
say "Pulling primary model: $PRIMARY_MODEL (~5 GB, can take several minutes)..."
if ollama list 2>/dev/null | grep -qF "$PRIMARY_MODEL"; then
    ok "Primary model already pulled."
else
    if ! ollama pull "$PRIMARY_MODEL"; then
        warn "Failed to pull $PRIMARY_MODEL — trying fallback qwen2.5-coder:7b ..."
        ollama pull qwen2.5-coder:7b
        PRIMARY_MODEL="qwen2.5-coder:7b"
    fi
fi

# ---------- 7. Try Qwen3-Coder (non-fatal) ----------
say "Trying optional model qwen3-coder:7b ..."
ollama pull qwen3-coder:7b 2>/dev/null && ok "qwen3-coder:7b pulled." || warn "qwen3-coder:7b unavailable, skipping."

# ---------- 8. Smoke test ----------
say "Smoke-testing model..."
SMOKE=$(curl -s http://127.0.0.1:11434/api/generate \
    -d "{\"model\":\"$PRIMARY_MODEL\",\"prompt\":\"Return only the JSON: {\\\"ok\\\":true}\",\"stream\":false,\"format\":\"json\"}" \
    | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('response','')[:200])" 2>/dev/null || echo "")
[[ -n "$SMOKE" ]] && ok "Model responded: $SMOKE" || warn "Smoke test produced no response (model may be loading)."

# ---------- 9. Python venv ----------
say "Setting up Python venv..."
if [[ ! -d .venv ]]; then
    "$PY312" -m venv .venv
fi
.venv/bin/pip install --quiet --upgrade pip wheel
.venv/bin/pip install --quiet -r requirements.txt
.venv/bin/pip install --quiet -e .
ok "venv ready at .venv"

# ---------- 10. .env ----------
if [[ ! -f .env ]]; then
    cp .env.example .env
    # Sync OLLAMA_MODEL with what we actually pulled
    sed -i.bak "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=$PRIMARY_MODEL|" .env && rm -f .env.bak
    ok "Created .env from .env.example (model = $PRIMARY_MODEL)"
fi

# ---------- 11. Done ----------
cat <<EOF

${GRN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}
${GRN} CodeSentinel AI — setup complete${NC}
${GRN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}

  Activate venv:    ${BLU}source .venv/bin/activate${NC}
  Verify env:       ${BLU}make doctor${NC}
  Run demo (CLI):   ${BLU}make demo${NC}
  Launch web UI:    ${BLU}make web${NC}
  Run tests:        ${BLU}make test${NC}

Primary model: ${PRIMARY_MODEL}
Web UI:        http://127.0.0.1:7860 (after make web)

EOF
