# Limitations

We list honest limitations of the system as it stands. None are blockers for the project's stated scope, but a future maintainer should know them.

## LLM-related

1. **Single-file context.** The model sees only the file under review. It cannot reason about callers in other files, type definitions in imports, or the project's overall architecture. A function with a misleading name can silently bypass detection.
2. **No memory across files.** Findings on file A do not inform the review of file B. We pay the full prompt cost on every file.
3. **7B is small.** A 70B+ model would catch subtler bugs (race conditions, off-by-one in non-trivial loops, semantic test gaps). The trade-off is hardware: 70B Q4_K_M requires ~40 GB unified RAM, beyond a typical student laptop.
4. **Training cutoff.** Qwen2.5-Coder's training data ends mid-2024. Code that uses post-cutoff APIs may receive outdated suggestions.
5. **English-centric.** Spanish docstrings or identifiers degrade detection quality slightly. We did not test for this rigorously.
6. **Determinism.** Even with `temperature=0.2`, two runs on the same file can produce slightly different counts (typically ±1 finding).

## Engineering

7. **No cross-language analysers.** We integrate bandit/ruff for Python and ESLint for JS/TS. Java and Go rely purely on the LLM. semgrep is listed in requirements but not yet wired up.
8. **Chunking is line-based, not AST-based.** Files > 1 500 lines are split with a 50-line overlap; a long class straddling a boundary loses some context. An AST-aware splitter would be better.
9. **No streaming UI.** The web UI shows a spinner during the entire 10-60 s call; we don't stream tokens. This is intentional (we need structured JSON), but feels slow.
10. **No multi-tenancy.** Gradio's queue is set to `concurrency=1`. Two users on the same instance will serialise.
11. **No persistent history.** Every review starts fresh; there is no "last 10 reviews" page.
12. **macOS-first.** The setup script is tested on Apple Silicon. Linux works but is unverified; Windows is unsupported.
13. **Static analysers must be in the same venv.** If a user activates a different venv, the Python-package analysers (bandit, ruff) disappear. We mitigate by searching the current interpreter's `bin/` directory.

## Methodological

14. **Self-graded results.** [07_results.md](07_results.md) compares findings against bugs *we ourselves* planted in fixtures. A blind evaluation on a public defect dataset (e.g. Defects4J, BigVul) is future work.
15. **No accuracy number on real codebases.** We have not measured precision/recall on an external project.

## Operational

16. **First-run latency.** The cold-start of ~55 s on the M5 is a poor first impression. We pre-warm in the demo by running multiple reviews in sequence.
17. **5 GB model download.** Onboarding a teammate requires patience while Ollama pulls the model on first run.
18. **No Docker on Mac.** Ollama in Docker on macOS doesn't use Metal — much slower. We document the host-runtime requirement in `deploy/README.md`.
