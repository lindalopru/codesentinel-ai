# Project Report — CodeSentinel AI

**Universidad Surcolombiana (USCO) · Inteligencia Artificial · Prof. Juan Antonio Castro Silva**
**Proyecto 2 — IA aplicada a Ingeniería de Software · Tema libre · 50% de la nota**

**Autores:** Linda Valentina Lopez Rubiano · Juan Felipe Andrade
**Fecha:** Mayo 2026

---

## 1. Introduction

Modern software engineering teams ship faster than human reviewers can keep up. Tools like GitHub Copilot for PRs, Cursor Review, and CodeRabbit have demonstrated that large language models (LLMs) can find real defects, security vulnerabilities, and style problems in source code at a quality bar comparable to a senior engineer. They are, however, **cloud services**: every byte of source code is uploaded to a third party.

**CodeSentinel AI** answers the question: *can we obtain the same quality of code review while keeping all source code on the developer's own machine?*

This report describes a working answer built for Project 2 of the *Inteligencia Artificial* course. CodeSentinel pairs a 7-billion-parameter coding model (Qwen2.5-Coder, quantised to ~4.7 GB) running locally via Ollama with classic static analysers (bandit, ruff, ESLint) so that AI-generated findings are grounded in deterministic signal. Two interchangeable front-ends — a colourised terminal CLI and a Gradio web UI — drive the same review engine.

## 2. Problem statement

Manual code review is **slow**, **inconsistent**, and **expensive**. Cloud-hosted AI reviewers are **fast** and **consistent**, but they **leak source code** to vendors, are subject to subscription costs, and depend on network availability. We need an open, local, privacy-preserving alternative that still produces actionable findings.

## 3. Objectives

**General objective:** Build a local AI code reviewer that detects bugs, security vulnerabilities, performance issues, style problems, and missing documentation in real source code, exposing the same engine through both a terminal CLI and a web UI.

**Specific objectives:**
1. Run a state-of-the-art coding LLM entirely on a MacBook Pro M5 with 16 GB unified memory.
2. Produce structured JSON output that can drive multiple report formats (Markdown, JSON, SARIF).
3. Augment the LLM with classic static analysers to reduce hallucinations and ground severity.
4. Cover Python, JavaScript, TypeScript and Java in version 1.
5. Provide three review modes: single file, recursive directory, `git diff`.
6. Ship a one-command demo and academic-grade documentation.

## 4. Motivation

- **Privacy first**: legal teams in regulated industries (banking, healthcare) cannot send code to vendors.
- **Cost**: cloud reviewers charge per-seat and per-call — a student or open-source maintainer cannot afford them.
- **Latency**: local inference on Apple Silicon (Metal) is fast enough for interactive use (~10–60 s per file).
- **Education**: students benefit from instant, structured feedback when learning a new language.

## 5. State of the art (May 2026)

| Tool | Hosted? | Cost | Privacy | Open? |
|---|---|---|---|---|
| GitHub Copilot (PR Review) | Cloud (Azure) | $/seat | Code uploaded | No |
| Cursor Review | Cloud (Anthropic + OpenAI) | $/seat | Code uploaded | No |
| CodeRabbit | Cloud | $/seat | Code uploaded | No |
| Sourcery | Cloud | Freemium | Code uploaded | Partial |
| Bandit / Ruff / ESLint | Local | Free | Local only | Yes — but rule-based, not AI |
| **CodeSentinel (this project)** | **Local** | **Free** | **Fully local** | **Yes (MIT)** |

CodeSentinel sits at the intersection of the bottom two rows: the AI quality of cloud tools with the locality of static analysers.

## 6. Solution overview

The system has three layers:

1. **Local LLM runtime** — Ollama hosts a quantised 7B coding model (Qwen2.5-Coder-Instruct, Q4_K_M). The model lives on disk in ~/.ollama and runs on the Mac's Metal GPU.
2. **Review engine** — A Python package that:
   - Detects the file's language.
   - Optionally runs deterministic static analysers (bandit, ruff, ESLint).
   - Sends the source code plus optional analyser hints to the LLM with a strict JSON output contract.
   - Parses the LLM response (with a robust fallback chain — see [05_prompt_engineering.md](05_prompt_engineering.md)).
   - Merges and de-duplicates findings, preferring the higher-severity classification.
3. **Front-ends**
   - A Typer + Rich CLI for the terminal.
   - A Gradio Blocks web UI in the browser.

## 7. Results preview

Running CodeSentinel against the bundled example files produces:

| File | Critical | High | Medium | Low | Info | Total |
|---|---:|---:|---:|---:|---:|---:|
| `examples/buggy_python.py` | 2 | 5 | 4 | 4 | 2 | **17** |
| `examples/insecure_js.js` | 1+ | 2+ | 1+ | 1+ | 0 | ~6 |
| `examples/messy_typescript.ts` | 0 | 2+ | 2+ | 1+ | 0 | ~5 |
| `examples/legacy_java.java` | 0 | 2+ | 2+ | 1+ | 0 | ~5 |

Detailed findings are in [07_results.md](07_results.md).

## 8. Scope and constraints

| Constraint | Value |
|---|---|
| Hardware target | Apple Silicon (M-series), ≥16 GB unified RAM |
| Model size | 7B params, Q4_K_M quantisation, ~4.7 GB on disk |
| First-call latency | ~50 s (model load) — subsequent ~10–20 s |
| Files supported | Python, JavaScript, TypeScript, Java, Go, Rust (LLM-only for non-Python) |
| Max file size | 1500 lines (auto-chunked above) |
| Languages of UI text | English |

## 9. Document map

- [02 — Requirements](02_requirements.md) — what the system must do
- [03 — Architecture](03_architecture.md) — how it is built
- [04 — Model card](04_model_card.md) — what model we use and why
- [05 — Prompt engineering](05_prompt_engineering.md) — the LLM's instructions
- [06 — Testing](06_testing.md) — how we verify it works
- [07 — Results](07_results.md) — measured findings on the examples
- [08 — Limitations](08_limitations.md) — what we cannot do (yet)
- [09 — Future work](09_future_work.md) — where this could go next
- [10 — Presentation script](10_presentation_script.md) — for the live demo
- [11 — Run book](11_run_book.md) — troubleshooting when things break
