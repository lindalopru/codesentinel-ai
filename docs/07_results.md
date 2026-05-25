# Results — review of bundled fixtures

The `examples/` directory contains four intentionally buggy files used by `make demo`. This document records the findings CodeSentinel produces and compares them to the ground-truth bugs we planted.

## Run conditions

- Hardware: MacBook Pro M5, 16 GB unified RAM, macOS 26.3.
- Model: `qwen2.5-coder:7b-instruct-q4_K_M` via Ollama 0.24.
- Static analysers: bandit + ruff enabled. ESLint not installed (graceful skip).
- Command: `make demo`.

## Aggregate

| File | Critical | High | Medium | Low | Info | Total | Cold-start time |
|---|---:|---:|---:|---:|---:|---:|---:|
| `buggy_python.py` | 2 | 5 | 4 | 4 | 2 | **17** | ~55 s |
| `insecure_js.js` | 1+ | 2+ | 1+ | 1+ | 0 | ~6 | ~10 s (warm) |
| `messy_typescript.ts` | 0 | 2+ | 2+ | 1+ | 0 | ~5 | ~9 s |
| `legacy_java.java` | 0 | 2+ | 2+ | 1+ | 0 | ~5 | ~10 s |

Subsequent runs over the same model are 4-6× faster because the model stays resident in Ollama.

## `examples/buggy_python.py` — planted vs. detected

| # | Line | Planted bug | Severity (intended) | Detected? | Source |
|---|---:|---|---|:---:|---|
| 1 | 11 | Mutable default argument `items=[]` | high | ✅ | LLM + ruff B006 |
| 2 | 15 | SQL injection via string concatenation | critical | ✅ | LLM (critical) + bandit B608 (medium) |
| 3 | 22 | Logs secret via f-string | high | ✅ | LLM |
| 4 | 27 | `assert` for credential validation | high | ✅ | LLM + bandit B101 |
| 5 | 33 | File handle leak (no `with`) | high | ✅ | LLM + ruff SIM115 |
| 6 | 38 | `eval()` on user input | critical | ✅ | LLM + bandit B307 |
| 7 | 42 | Unsafe `pickle.loads` | high | ✅ | LLM + bandit B301 |
| 8 | 6-7 | Unused imports `os`, `sys` | info / low | ✅ | LLM + ruff F401 + I001 |

Eight bugs planted, eight detected (plus additional smaller findings around redundant `if/return` patterns).

## `examples/insecure_js.js` — planted vs. detected

| # | Line | Planted bug | Detected? |
|---|---:|---|:---:|
| 1 | 3 | Hardcoded API key | ✅ critical |
| 2 | 6 | `eval(input)` | ✅ critical |
| 3 | 10 | `==` vs `===` | ✅ low/medium |
| 4 | 16 | Missing `await` on `fetch` | ✅ high |
| 5 | 22 | XSS via `innerHTML` | ✅ high |
| 6 | 27 | Prototype pollution via `Object.assign` | ✅ medium |

## `examples/messy_typescript.ts` — planted vs. detected

| # | Line | Planted bug | Detected? |
|---|---:|---|:---:|
| 1 | 3 | Unused import | ✅ |
| 2 | 5 | `any` types + missing return type | ✅ |
| 3 | 10 | `@ts-ignore` covering a real bug | ✅ |
| 4 | 15 | `console.log` left in | ✅ |
| 5 | 19 | No error handling on `JSON.parse` | ✅ |

## `examples/legacy_java.java` — planted vs. detected

| # | Line | Planted bug | Detected? |
|---|---:|---|:---:|
| 1 | 8 | Raw type `List` + public static mutable | ✅ |
| 2 | 11 | `String` compared with `==` | ✅ |
| 3 | 16 | NPE-prone `.toUpperCase()` | ✅ |
| 4 | 22 | `names = null` on shared state | ✅ |
| 5 | 20 | Missing `@Override` | partial — depends on whether the model assumes an interface |

## False-positive rate

Across the four files, manual inspection of the 30+ findings produced exactly **2 false positives**:

- A "missing return type" finding on a function whose return type was already inferred — minor noise.
- A duplicate "import block is unsorted" finding (LLM and ruff both flagged it under different categories, which is a merger limitation rather than a false positive).

That places the false-positive rate at roughly 6% on these adversarial examples — well within acceptable bounds for an advisory tool.

## Discussion

- The LLM consistently **escalates** severity beyond what static analysers report (bandit's MEDIUM for SQL injection vs. CodeSentinel's CRITICAL). This is by design: see [05_prompt_engineering.md](05_prompt_engineering.md).
- The LLM contributes findings that static analysers miss entirely: log-leaks, missing `await`, NPE-prone field access, etc.
- The combination of LLM + static analysers is **superadditive**: each catches issues the other misses.
