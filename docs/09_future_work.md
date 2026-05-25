# Future work

Roughly ordered by impact-per-effort:

## Near term (1–2 weeks each)

1. **Cross-file context.** Use tree-sitter to extract the import graph of the file under review, fetch the imported symbols' source, and include them in the prompt. Likely 10-30% precision gain on bug categories like type mismatches and contract violations.
2. **AST-aware chunker.** Replace line-based chunking with a tree-sitter splitter that respects class/function boundaries.
3. **Streaming UI.** Replace the spinner with token-by-token streaming. Keep the final JSON validation step; show progressive prose during generation.
4. **Per-language prompts.** A Python prompt that mentions PEP 8, a JS prompt that mentions ESLint conventions, a Java prompt that mentions checkstyle. Currently the prompt is language-agnostic.
5. **Pre-commit hook.** Ship a `codesentinel diff --staged --fail-on high` integration as a [pre-commit](https://pre-commit.com) plugin.

## Medium term (1–3 months)

6. **VS Code extension.** A thin TypeScript extension (~200 LoC) that shells out to the CLI and renders findings in the Problems panel. The SARIF output is already there.
7. **GitHub Action.** A workflow that runs CodeSentinel on PRs, posts findings as review comments, and exits non-zero on critical issues.
8. **External benchmark.** Evaluate on a public defect dataset (Defects4J for Java, BugsInPy for Python). Publish precision/recall numbers in [07_results.md](07_results.md).
9. **Larger models gated by RAM.** Auto-detect available RAM and offer Codestral 22B or DeepSeek-Coder-V2 16B when it fits.
10. **Specialised fine-tune.** Train a LoRA adapter on top of Qwen2.5-Coder using the project's own historical bug fixes. Expected gain: improvements on patterns specific to the user's codebase.

## Long term

11. **Multi-agent review.** Separate agents for security, performance, style, and docs, each with its own prompt and model. Cross-vote to reduce false positives.
12. **Live IDE integration.** Inline annotations that update as the user types, throttled to debounce.
13. **Educational mode.** For students: show *why* a bug matters and link to a primer (e.g. SQL injection → OWASP cheatsheet).
14. **Voice review.** Read the report aloud — useful for accessibility and review-on-the-go.
15. **Mobile companion app.** Push critical findings as notifications.
