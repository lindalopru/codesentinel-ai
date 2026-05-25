# Deployment notes

CodeSentinel was designed to run on a developer's local machine, but the
`docker-compose.yml` at the project root supports a server deployment scenario.

## macOS — host runtime is fastest

On Apple Silicon Macs, **Ollama in Docker does NOT use Metal acceleration** and
runs ~3-5× slower than the host runtime. Recommended setup on a Mac:

```bash
brew install --cask ollama-app   # daemon on host with Metal
make web                          # Gradio in venv on host
```

## Linux server / cloud

The Docker stack is useful for self-hosting CodeSentinel on a Linux server:

```bash
docker compose up -d
# First-time pull of the model inside the ollama container
docker compose exec ollama ollama pull qwen2.5-coder:7b-instruct-q4_K_M
```

The web service is available at <http://localhost:7860>. The web container
talks to the Ollama container on the internal `ollama:11434` address.

## Resource requirements

- ~5 GB disk for the model
- 8 GB RAM minimum (16 GB recommended)
- GPU optional but recommended on Linux (CUDA — Ollama auto-detects)

## Security

- The web UI is bound to `0.0.0.0:7860` in the container. Behind a reverse proxy,
  add HTTPS and authentication. The default deployment is NOT internet-safe.
- No telemetry. No outbound network calls.
