# Model Card — Qwen2.5-Coder 7B Instruct (Q4_K_M)

## Model details

| Field | Value |
|---|---|
| Family | Qwen2.5-Coder (Alibaba DAMO Academy) |
| Variant | 7B-Instruct, Q4_K_M GGUF |
| Ollama tag | `qwen2.5-coder:7b-instruct-q4_K_M` |
| Parameters | 7.62 B |
| Context window | 32 k tokens (Ollama capped to 16 384 by default in our config) |
| Disk size | ~ 4.7 GB |
| Licence | Apache 2.0 (model weights) |
| Quantisation | Q4_K_M (4-bit, mixed) |
| Original paper | "Qwen2.5-Coder Technical Report", arXiv:2409.12186 (2024) |

## Why this model

- **Coding benchmarks**: HumanEval 76+, MBPP 70+ — top of its size class as of mid-2026.
- **JSON discipline**: Qwen-Coder family is heavily fine-tuned on function-calling and JSON output, making it reliable under Ollama's `format="json"` constrained decoding.
- **Hardware fit**: Q4_K_M fits comfortably in 16 GB unified memory while leaving room for the Gradio process and the OS.
- **Speed**: 40-80 tokens/s on Apple M5 via Metal — interactive enough for code review.
- **Licence**: Apache 2.0 weights — usable in academic and open-source contexts without restrictions.
- **Availability**: pre-built GGUF in the Ollama registry — no manual conversion.

## Models considered

| Model | Why rejected for this project |
|---|---|
| `codellama:7b` | Older (2023), much weaker on Python and TS than Qwen2.5-Coder. |
| `deepseek-coder-v2:lite` (16B MoE) | Bigger, slower to load; better quality marginal vs Qwen 7B on our examples. |
| `codestral:22b` | Too large for 16 GB; would swap. |
| `qwen3-coder:7b` (if available) | Tried as alternate tag in setup; not consistently available on Ollama registry yet. |

## Intended use

- AI-assisted code review on local source code.
- Educational use in software engineering courses.
- Demonstration of local-LLM tooling.

## Out-of-scope use

- Safety-critical decisions (medical, legal, financial)
- Source code generation for production deployment without human review
- Personally identifiable information processing
- Tasks outside software engineering (general chat, content generation)

## Known biases and failure modes

- **English-centric**: the model is most fluent when prompts and code comments are in English. Mixed-language docstrings (e.g. Spanish + English) may degrade quality slightly.
- **Recency cut-off**: training data ends mid-2024; very recent libraries (post-cutoff) may receive outdated suggestions.
- **Over-confident on small snippets**: ≤ 3 lines of code can prompt confident but spurious findings — we filter using static analysers and the merger.
- **Verbose suggestions**: occasionally rewrites large blocks instead of small fixes — clip suggestions to ~6 lines in the UI.
- **JSON drift**: under high temperature can emit stray markdown fences — handled by [05_prompt_engineering.md](05_prompt_engineering.md)'s fallback parser.

## Performance characteristics (measured on M5, 16 GB RAM)

| Metric | Value |
|---|---|
| Cold-start latency (first call, model load + inference) | ~ 55 s |
| Warm-start latency (subsequent calls) | ~ 10-20 s |
| Throughput | 40-80 tokens/s |
| Memory during inference | ~ 6 GB |
| GPU usage | Metal, automatic |
| Concurrency | Engine limited to 2 simultaneous calls to avoid OOM |

## Environmental impact

Local inference on consumer hardware. Estimated energy per review: < 0.01 kWh. No data centre cost.

## Ethical considerations

- No source code leaves the developer's machine.
- All weights are open-source under Apache 2.0.
- The model does not generate or store user data beyond the current process.
- The tool is non-authoritative: findings are advisory; humans remain the final reviewer.
