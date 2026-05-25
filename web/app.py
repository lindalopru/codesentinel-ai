"""CodeSentinel AI — Gradio web UI."""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

import gradio as gr

from codesentinel import __version__
from codesentinel.config import get_settings
from codesentinel.languages import EXTENSION_MAP
from codesentinel.llm.client import OllamaClient
from codesentinel.reporting import to_markdown
from codesentinel.review import ReviewEngine
from codesentinel.schema import ReviewResult, Severity
from web.components import render_findings_html, severity_counts

# -------- shared state --------

_settings = get_settings()
_client = OllamaClient(_settings)
_engine = ReviewEngine(client=_client, settings=_settings)

CSS_PATH = Path(__file__).parent / "assets" / "styles.css"
CSS = CSS_PATH.read_text(encoding="utf-8") if CSS_PATH.exists() else ""

LANGUAGE_CHOICES = ["auto"] + sorted({v for v in EXTENSION_MAP.values()})
SEVERITY_CHOICES = [s.value for s in Severity]

ABOUT_MD = f"""
## CodeSentinel AI v{__version__}

**Local AI Code Reviewer** — Runs entirely on your Mac via Ollama + Qwen2.5-Coder.
No code leaves your machine. No API keys. No cloud.

- **Model in use:** `{_settings.ollama_model}`
- **Ollama host:** `{_settings.ollama_host}`
- **Context window:** `{_settings.ollama_num_ctx}` tokens

### Features
- Detects bugs, security issues, performance problems, style violations, and missing docs.
- Augments the LLM with classic static analysers (bandit, ruff, ESLint) to ground findings.
- Five severity levels: critical · high · medium · low · info.
- Multi-language: Python, JavaScript, TypeScript, Java, Go, Rust, and more.
- Three modes: single file, paste-and-go, git diff.

Built for Project 2 of *Inteligencia Artificial*, USCO.
"""

# -------- handlers --------


def _save_md_report(results: ReviewResult | list[ReviewResult]) -> str:
    md = to_markdown(results)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    tmp = Path(tempfile.gettempdir()) / f"codesentinel_{ts}.md"
    tmp.write_text(md, encoding="utf-8")
    return str(tmp)


def _resolve_model(selected: str) -> OllamaClient:
    selected = (selected or "").strip()
    if not selected or selected == _settings.ollama_model:
        return _client
    return OllamaClient(_settings, model=selected)


def _resolve_engine(selected_model: str) -> ReviewEngine:
    c = _resolve_model(selected_model)
    if c is _client:
        return _engine
    return ReviewEngine(client=c, settings=_settings)


def review_uploaded_file(
    file_obj, model: str, language: str, min_sev: str, use_static: bool
):
    if file_obj is None:
        return "<i>Upload a file to begin.</i>", [], None, "Idle."
    path = Path(file_obj.name)
    engine = _resolve_engine(model)
    result = engine.review_file(path, use_static=use_static)
    if language and language != "auto":
        result.language = language
    result = result.filter_by_severity(Severity(min_sev))
    md_path = _save_md_report(result)
    return (
        render_findings_html(result),
        severity_counts(result),
        md_path,
        f"Done in {result.duration_s:.1f}s · {len(result.findings)} finding(s).",
    )


def review_pasted_code(
    code: str, model: str, language: str, min_sev: str, use_static: bool
):
    if not code or not code.strip():
        return "<i>Paste some code to begin.</i>", [], None, "Idle."
    lang = language if language and language != "auto" else "python"
    engine = _resolve_engine(model)
    # Static analyzers need a real file path; write to a temp file so bandit/ruff can run.
    if use_static:
        ext = next((e for e, name in EXTENSION_MAP.items() if name == lang), ".txt")
        tmp = Path(tempfile.mkdtemp()) / f"pasted{ext}"
        tmp.write_text(code, encoding="utf-8")
        result = engine.review_file(tmp, use_static=True)
        result.file_path = "pasted snippet"
    else:
        result = engine.review_source(code, language=lang, file_path="pasted snippet", use_static=False)
    result = result.filter_by_severity(Severity(min_sev))
    md_path = _save_md_report(result)
    return (
        render_findings_html(result),
        severity_counts(result),
        md_path,
        f"Done in {result.duration_s:.1f}s · {len(result.findings)} finding(s).",
    )


def review_git_diff_handler(repo_path: str, ref: str, staged: bool, model: str, min_sev: str, use_static: bool):
    if not repo_path or not Path(repo_path).exists():
        return "<i>Provide a valid repository path.</i>", [], None, "Idle."
    engine = _resolve_engine(model)
    results = engine.review_diff(Path(repo_path), ref=ref or "HEAD", staged=staged, use_static=use_static)
    if not results:
        return "<div class='summary-banner'>No reviewable changes detected.</div>", [], None, "Done."
    results = [r.filter_by_severity(Severity(min_sev)) for r in results]
    md_path = _save_md_report(results)
    total_findings = sum(len(r.findings) for r in results)
    return (
        render_findings_html(results),
        severity_counts(results),
        md_path,
        f"Reviewed {len(results)} file(s), {total_findings} finding(s).",
    )


# -------- UI layout --------


def build_ui() -> gr.Blocks:
    pulled = _client.list_models()
    model_choices = pulled if pulled else [_settings.ollama_model]
    default_model = _settings.ollama_model if _settings.ollama_model in model_choices else model_choices[0]

    with gr.Blocks(title="CodeSentinel AI", theme=gr.themes.Soft(), css=CSS) as demo:
        gr.Markdown(
            f"# 🛡️ CodeSentinel AI\n"
            f"*Local AI Code Reviewer · running on `{_settings.ollama_model}` via Ollama · v{__version__}*"
        )

        with gr.Row():
            model_dd = gr.Dropdown(choices=model_choices, value=default_model, label="Model", scale=2)
            lang_dd = gr.Dropdown(choices=LANGUAGE_CHOICES, value="auto", label="Language", scale=1)
            sev_dd = gr.Dropdown(choices=SEVERITY_CHOICES, value="info", label="Min severity", scale=1)
            static_cb = gr.Checkbox(value=True, label="Augment with static analyzers", scale=1)

        with gr.Tabs():
            with gr.Tab("📁 Upload file"):
                file_in = gr.File(file_types=[".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".rb", ".php", ".kt", ".cpp", ".c"], label="Source file")
                file_btn = gr.Button("🔍 Review file", variant="primary")

            with gr.Tab("📝 Paste code"):
                code_in = gr.Code(language="python", lines=18, label="Paste code here")
                paste_btn = gr.Button("🔍 Review code", variant="primary")

            with gr.Tab("🔀 Git diff"):
                with gr.Row():
                    repo_in = gr.Textbox(label="Repository path", value=str(Path.cwd()))
                    ref_in = gr.Textbox(label="Compare to ref", value="HEAD")
                    staged_cb = gr.Checkbox(value=False, label="Staged only")
                diff_btn = gr.Button("🔍 Review diff", variant="primary")

            with gr.Tab("ℹ️ About"):
                gr.Markdown(ABOUT_MD)

        status = gr.Markdown(value="_Idle._")

        with gr.Row():
            with gr.Column(scale=2):
                findings_out = gr.HTML(label="Findings", value="<div class='summary-banner'>Findings will appear here.</div>")
            with gr.Column(scale=1):
                counts_out = gr.Dataframe(
                    headers=["Severity", "Count"],
                    label="Totals by severity",
                    interactive=False,
                    value=[["CRITICAL", 0], ["HIGH", 0], ["MEDIUM", 0], ["LOW", 0], ["INFO", 0]],
                )
                report_dl = gr.File(label="Download Markdown report", interactive=False)

        file_btn.click(
            review_uploaded_file,
            inputs=[file_in, model_dd, lang_dd, sev_dd, static_cb],
            outputs=[findings_out, counts_out, report_dl, status],
            queue=True,
            show_progress="full",
        )
        paste_btn.click(
            review_pasted_code,
            inputs=[code_in, model_dd, lang_dd, sev_dd, static_cb],
            outputs=[findings_out, counts_out, report_dl, status],
            queue=True,
            show_progress="full",
        )
        diff_btn.click(
            review_git_diff_handler,
            inputs=[repo_in, ref_in, staged_cb, model_dd, sev_dd, static_cb],
            outputs=[findings_out, counts_out, report_dl, status],
            queue=True,
            show_progress="full",
        )

    return demo


def main() -> None:
    import os

    # Privacy: never phone home — this is a local-first tool.
    os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

    demo = build_ui()
    host = os.environ.get("CODESENTINEL_WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("CODESENTINEL_WEB_PORT", "7860"))
    demo.queue(default_concurrency_limit=1).launch(
        server_name=host,
        server_port=port,
        inbrowser=False,
        share=False,
    )


if __name__ == "__main__":
    main()
