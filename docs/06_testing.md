# Testing

## Strategy

CodeSentinel mixes deterministic Python code with a non-deterministic LLM. Our test strategy splits accordingly:

| Layer | Determinism | Strategy |
|---|---|---|
| Schema, parser, prompts, merger, chunker, git_diff, languages, reporting | Fully deterministic | Pure unit tests. |
| LLM client | Deterministic given HTTP response | `respx` mocks the Ollama HTTP API. |
| Review engine | Deterministic given LLM response | Inject a fake client implementing the same interface. |
| Analyzers (bandit/ruff/eslint) | Subprocess-dependent | Smoke tests through the engine; mocked at the `_FakeClient` level so engine tests stay fast. |
| End-to-end | Requires real Ollama + model | `make demo` — a live integration smoke. |

## Test inventory

| File | Coverage |
|---|---|
| `tests/test_schema.py` | Severity ordering, Finding round-trip, line-range clamping, filter_by_severity. |
| `tests/test_parser.py` | 12 nasty real-world LLM outputs (fences, BOM, trailing commas, json5, prose, garbled). |
| `tests/test_prompts.py` | System prompt contains contract, few-shot is valid JSON, numbered lines, augmentation rendering, message composition. |
| `tests/test_chunker.py` | Small file → single chunk, large file → overlapping chunks, coverage of all lines. |
| `tests/test_merger.py` | Disjoint findings kept, similar findings deduped with severity upgrade, sort order. |
| `tests/test_git_diff.py` | Multi-file diff parsing, empty diff returns empty. |
| `tests/test_languages.py` | Python / TS detection, unknown extension fallback, display names. |
| `tests/test_reporting.py` | JSON round-trip, Markdown rendering, SARIF schema compliance. |
| `tests/test_client.py` | respx-mocked: success, JSON retry, double-failure raises, HTTP error, list_models. |
| `tests/test_engine.py` | review_file with mocked LLM, severity filter, diff_lines filter, drops bad findings. |
| `tests/test_engine_dir.py` | review_dir includes/excludes, empty directories. |
| `tests/test_cli.py` | Typer help, version, subcommand listing, missing-file handling. |

## Coverage

After `make test`:

| Module | Statements | Coverage |
|---|---:|---:|
| `parser.py` | 80 | 99% |
| `schema.py` | 55 | 100% |
| `merger.py` | 29 | 100% |
| `prompts.py` | 17 | 100% |
| `chunker.py` | 24 | 96% |
| `reporting/markdown.py` | 45 | 93% |
| `reporting/sarif.py` | 15 | 100% |
| `reporting/json_report.py` | 7 | 86% |
| `review/engine.py` | 126 | 70% |
| `llm/client.py` | 84 | 65% |
| `languages.py` | 10 | 100% |
| `config.py` | 23 | 100% |
| Analyzers (subprocess-bound) | 168 | ~35% |
| Doctor (CLI) | 66 | 0% (manual smoke) |
| **TOTAL** | **834** | **70%** |

Core packages (parser / schema / merger / prompts / chunker) exceed 95%. Lower-coverage modules are subprocess-heavy or CLI-presentation code.

## Manual UI checklist

For the web UI, the verification is manual (Gradio's interaction tests would require Playwright, overkill here):

- [ ] `make web` opens <http://127.0.0.1:7860> without errors.
- [ ] Upload tab: drag `examples/buggy_python.py`, click Review → ≥ 6 findings rendered.
- [ ] Paste tab: paste the same content + language=python → similar findings.
- [ ] Git diff tab: point at the project's own repo, click Review → completes (may be empty if no changes).
- [ ] Severity dropdown filters findings live.
- [ ] Model dropdown lists pulled models.
- [ ] Static-analyser checkbox toggle changes results.
- [ ] Download Markdown report produces a non-empty `.md` file.
- [ ] About tab renders model name and version.

## How to run

```bash
make test       # all tests, with coverage
make lint       # ruff + black --check + mypy
make demo       # end-to-end smoke with real Ollama
make doctor     # environment health
```

CI is not configured for this academic project (no `.github/workflows`), but the Makefile targets are scriptable.
