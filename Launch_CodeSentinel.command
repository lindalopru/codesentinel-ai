#!/usr/bin/env bash
# Double-click this file from Finder to open CodeSentinel as a desktop app.
#
# What happens:
#   1. Switches to the project directory.
#   2. Activates the Python virtual environment.
#   3. Starts a native window powered by pywebview + the Gradio UI.
#
# Close the window when you're done — the server stops automatically.

set -e
cd "$(dirname "$0")"

if [[ ! -d ".venv" ]]; then
    echo "venv missing. Run 'bash setup.sh' first."
    read -p "Press Enter to close..."
    exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

# Make sure the Ollama daemon is up — start headless if not.
if ! curl -sf http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
    if command -v ollama >/dev/null 2>&1; then
        nohup ollama serve >/tmp/ollama.log 2>&1 &
        # Give it a few seconds to bind
        for _ in 1 2 3 4 5 6 7 8 9 10; do
            if curl -sf http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
                break
            fi
            sleep 1
        done
    else
        echo "Ollama not installed. Run 'bash setup.sh' first."
        read -p "Press Enter to close..."
        exit 1
    fi
fi

exec python -m web.desktop
