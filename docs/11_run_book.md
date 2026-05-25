# Run book — troubleshooting

## "ollama: command not found"

```bash
brew install --cask ollama-app   # or: brew install ollama
```

If brew itself isn't installed:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

## "Ollama daemon not reachable on 127.0.0.1:11434"

```bash
# Start headless
nohup ollama serve > /tmp/ollama.log 2>&1 &

# Or open the GUI app
open -a Ollama

# Verify
curl -s http://127.0.0.1:11434/api/version
```

If the port is in use, find what's holding it:
```bash
lsof -i :11434
```

## "model 'qwen2.5-coder:7b-instruct-q4_K_M' not found"

```bash
ollama pull qwen2.5-coder:7b-instruct-q4_K_M
```

Takes 5-15 minutes depending on bandwidth. Pull is resumable; if it stalls, ctrl-C and re-run.

## "python3.12 not found"

```bash
brew install python@3.12
# Verify
python3.12 --version
```

## "ModuleNotFoundError: No module named 'codesentinel'"

You're running from a shell where the venv isn't active. Either:
```bash
source .venv/bin/activate
# or always use the venv's python directly:
.venv/bin/python -m cli.main --help
```

## ".venv broken / weird import errors"

```bash
make clean      # nukes .venv + caches
make install    # rebuilds
```

## "Port 7860 already in use" (Gradio web UI)

Another Gradio app is running. Kill it:
```bash
lsof -ti :7860 | xargs kill
```

Or change the port in [`web/app.py`](../web/app.py) (`server_port=7860`).

## CLI runs but no findings come back

1. Run `make doctor` — verify model is pulled and daemon is up.
2. Try a smaller file (≤ 30 lines).
3. Check `/tmp/ollama.log` for errors.
4. Lower `OLLAMA_NUM_CTX` to 4096 in `.env` if you're hitting OOM (rare on 16 GB).

## "LLM call failed twice" in logs

The model returned garbled output twice in a row. Causes:
- Model was just loaded and crashed → retry the command.
- Disk is full → `df -h`.
- File contains binary blobs → our reader tolerates them with `errors="replace"`, but the prompt may still confuse the model. Try with a shorter file.

## bandit / ruff are skipped

They live inside the venv. From outside the venv they're not on PATH. The doctor displays them as `SKIP` but they still work when the engine is invoked via `.venv/bin/python` or `make`.

Reinstall if you're sure they're missing:
```bash
.venv/bin/pip install --force-reinstall bandit==1.7.10 ruff==0.6.9
```

## "respx not installed" / test failures on import

```bash
.venv/bin/pip install -r requirements.txt
```

## Resetting everything from scratch

```bash
make clean
rm -rf ~/.ollama/models
bash setup.sh
```

The last command re-pulls the model (~5 GB). Use only if you suspect a corrupted model file.

## Performance is poor

- Confirm Metal is engaged: `top -pid $(pgrep ollama) -stats command,cpu,mem` — should show ~6 GB RSS and high CPU during inference.
- Check macOS Activity Monitor for thermal throttling.
- Close other heavy apps (Chrome, Docker) — they eat unified memory the model needs.
- Reduce `OLLAMA_NUM_CTX` in `.env` from 16384 to 8192.

## Logs

- Ollama: `/tmp/ollama.log` (started by `setup.sh`'s `nohup ollama serve`)
- CodeSentinel: stderr — set `CODESENTINEL_LOG_LEVEL=DEBUG` for verbose output.

## Getting help

- Open an issue on the GitHub repository.
- Check the model card: [04_model_card.md](04_model_card.md).
- Check known limitations: [08_limitations.md](08_limitations.md).
