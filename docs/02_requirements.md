# Requirements

## Functional requirements

| # | Requirement | Met by |
|---|---|---|
| F1 | Detect bugs, security issues, performance issues, style violations, and documentation gaps. | `codesentinel/llm/prompts.py` (5 categories enforced in the JSON schema) |
| F2 | Classify each finding into five severity levels (critical / high / medium / low / info). | `codesentinel.schema.Severity` |
| F3 | Run a local LLM with no network calls outside `127.0.0.1`. | Ollama on localhost — no telemetry |
| F4 | Support at least Python, JavaScript, TypeScript and Java. | `codesentinel.languages.EXTENSION_MAP` |
| F5 | Augment the LLM with classic static analysers (bandit, ruff, ESLint) when available. | `codesentinel/analyzers/*` |
| F6 | Review (a) a single file, (b) a directory recursively, (c) only the lines changed in a `git diff`. | `ReviewEngine.review_file / review_dir / review_diff` |
| F7 | Provide both a terminal CLI and a web UI. | `cli/main.py` + `web/app.py` |
| F8 | Emit the same findings in three report formats: pretty terminal, Markdown, JSON, and SARIF. | `codesentinel/reporting/*` |
| F9 | Filter findings by minimum severity (`--severity` flag, web-UI dropdown). | `ReviewResult.filter_by_severity` |
| F10 | Exit non-zero in CI mode if any finding ≥ a configurable threshold. | `cli/main.py --fail-on` |
| F11 | Provide a one-command demo running all example fixtures. | `make demo` |
| F12 | Provide a `doctor` command that diagnoses the local environment. | `codesentinel/utils/doctor.py` |
| F13 | Allow the user to switch models at runtime. | `--model` CLI flag and web-UI dropdown |

## Non-functional requirements

| # | Requirement | Target | Met by |
|---|---|---|---|
| N1 | Privacy | No network traffic to non-loopback addresses. | Ollama bound to `127.0.0.1`, no external API calls in the codebase. |
| N2 | First-review latency | ≤ 90 s on a cold start; ≤ 30 s on subsequent calls. | Qwen2.5-Coder 7B Q4_K_M on M5 Metal. |
| N3 | Memory footprint | ≤ 8 GB RAM during inference. | 7B Q4_K_M model + Python process |
| N4 | Disk footprint | ≤ 10 GB total. | 4.7 GB model + ~1 GB venv |
| N5 | Code coverage | ≥ 80 % on core packages (`parser`, `schema`, `merger`, `engine`, `chunker`, `prompts`). | 95-100% measured (see [06_testing.md](06_testing.md)) |
| N6 | Reproducibility | A single `bash setup.sh` brings up a fresh laptop end-to-end. | Idempotent setup script |
| N7 | Usability | New user can produce a review within 60 s of finishing setup. | `make demo` |
| N8 | Maintainability | Project conventions match the team's existing project structure. | Mirrors `~/Projects/beanguard-ai` |

## Out of scope (this iteration)

- IDE extension (VS Code, IntelliJ)
- GitHub Action / GitLab CI integration
- Cross-file context (the model only sees one file at a time)
- Fine-tuning on a custom dataset
- Non-Apple-Silicon optimisation (works on Linux but no Metal acceleration)
