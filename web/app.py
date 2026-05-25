"""CodeSentinel AI — Gradio web UI, premium edition."""

from __future__ import annotations

import os
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
from web.components import (
    EMPTY_STATE,
    render_findings_html,
    render_stats_html,
)

# -------- shared state --------

_settings = get_settings()
_client = OllamaClient(_settings)
_engine = ReviewEngine(client=_client, settings=_settings)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSS_PATH = Path(__file__).parent / "assets" / "styles.css"
CSS = CSS_PATH.read_text(encoding="utf-8") if CSS_PATH.exists() else ""

LANGUAGE_CHOICES = ["auto"] + sorted({v for v in EXTENSION_MAP.values()})
SEVERITY_CHOICES = [s.value for s in Severity]

# -------- sample fixtures (used by quick-start chips) --------

SAMPLES_DIR = PROJECT_ROOT / "examples"

SAMPLES = {
    "python": ("buggy_python.py", "python"),
    "javascript": ("insecure_js.js", "javascript"),
    "typescript": ("messy_typescript.ts", "typescript"),
    "java": ("legacy_java.java", "java"),
}


def _read_sample(key: str) -> tuple[str, str]:
    fname, lang = SAMPLES[key]
    p = SAMPLES_DIR / fname
    if not p.exists():
        return ("", lang)
    return (p.read_text(encoding="utf-8", errors="replace"), lang)


# -------- HERO HTML --------

HERO_HTML = f"""
<div class='cs-hero'>
  <div>
    <h1>CodeSentinel AI</h1>
    <p>Revisor de código con IA, ejecutándose 100% en tu Mac.</p>
  </div>
  <div class='cs-hero-meta'>
    <span class='cs-pill'><span class='dot'></span> Local</span>
    <span class='cs-pill'><code>{_settings.ollama_model.split(':')[0]}</code></span>
  </div>
</div>
"""

ABOUT_MD = f"""
### Cómo funciona

CodeSentinel combina un **modelo de lenguaje local** (Qwen2.5-Coder 7B vía Ollama) con
**analizadores estáticos clásicos** (bandit, ruff, ESLint) para detectar:

- 🚨 **Vulnerabilidades de seguridad** — SQL injection, XSS, eval(), secretos hardcoded
- 🐞 **Bugs** — default args mutables, NPE risk, recursos no cerrados
- ⚡ **Performance** — bucles N+1, I/O bloqueante
- 🎨 **Estilo** — imports sin usar, código muerto, convenciones
- 📚 **Documentación** — docstrings y comentarios faltantes

### Tres formas de usarlo

1. **Esta interfaz** (lo que estás viendo) — sube archivo, pega código o revisa un diff de git.
2. **CLI en terminal** — `codesentinel review archivo.py`
3. **App de escritorio** — `make desktop` o doble-clic en `Launch_CodeSentinel.command`

### Privacidad

Ningún byte de tu código sale de tu Mac. La única conexión de red es `127.0.0.1:11434`
hacia el daemon de Ollama, que corre completamente local.

---

**Configuración actual**
- Modelo: `{_settings.ollama_model}`
- Host: `{_settings.ollama_host}`
- Context window: `{_settings.ollama_num_ctx:,}` tokens
- Versión: **v{__version__}**

Proyecto 2 de *Inteligencia Artificial* — Universidad Surcolombiana (USCO).
"""

FOOTER_HTML = f"""
<div class='cs-footer'>
  <b>Linda Valentina Lopez Rubiano</b> &middot; <b>Juan Felipe Andrade</b>
  &middot; USCO &middot; v{__version__}
</div>
"""

PASTE_PLACEHOLDER = """def get_user(uid):
    query = "SELECT * FROM users WHERE id = " + str(uid)
    return db.execute(query)
"""

# -------- model loaders --------


def _resolve_client(selected_model: str) -> OllamaClient:
    selected = (selected_model or "").strip()
    if not selected or selected == _settings.ollama_model:
        return _client
    return OllamaClient(_settings, model=selected)


def _resolve_engine(selected_model: str) -> ReviewEngine:
    c = _resolve_client(selected_model)
    if c is _client:
        return _engine
    return ReviewEngine(client=c, settings=_settings)


def _save_md_report(results: ReviewResult | list[ReviewResult]) -> str:
    md = to_markdown(results)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    tmp = Path(tempfile.gettempdir()) / f"codesentinel_{ts}.md"
    tmp.write_text(md, encoding="utf-8")
    return str(tmp)


def _empty_outputs():
    return (
        EMPTY_STATE,
        render_stats_html(ReviewResult(file_path="", language="auto")),
        None,
        "Listo.",
    )


# -------- handlers --------


def review_uploaded_file(
    file_obj, model: str, language: str, min_sev: str, use_static: bool
):
    if file_obj is None:
        return ("<div class='cs-status'>⬆️ Sube un archivo para empezar.</div>",
                render_stats_html(ReviewResult(file_path="", language="auto")),
                None,
                "Listo.")
    path = Path(file_obj.name)
    engine = _resolve_engine(model)
    result = engine.review_file(path, use_static=use_static)
    if language and language != "auto":
        result.language = language
    result = result.filter_by_severity(Severity(min_sev))
    md_path = _save_md_report(result)
    n = len(result.findings)
    return (
        render_findings_html(result),
        render_stats_html(result),
        md_path,
        f"✓ Revisado en {result.duration_s:.1f}s · {n} hallazgo(s).",
    )


def review_pasted_code(
    code: str, model: str, language: str, min_sev: str, use_static: bool
):
    if not code or not code.strip():
        return ("<div class='cs-status'>📝 Pega código o usa un ejemplo de arriba.</div>",
                render_stats_html(ReviewResult(file_path="", language="auto")),
                None,
                "Listo.")
    lang = language if language and language != "auto" else "python"
    engine = _resolve_engine(model)
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
    n = len(result.findings)
    return (
        render_findings_html(result),
        render_stats_html(result),
        md_path,
        f"✓ Revisado en {result.duration_s:.1f}s · {n} hallazgo(s).",
    )


def review_git_diff_handler(repo_path: str, ref: str, staged: bool, model: str, min_sev: str, use_static: bool):
    if not repo_path or not Path(repo_path).exists():
        return ("<div class='cs-status'>📁 Provee la ruta a un repositorio git válido.</div>",
                render_stats_html(ReviewResult(file_path="", language="auto")),
                None,
                "Listo.")
    engine = _resolve_engine(model)
    results = engine.review_diff(Path(repo_path), ref=ref or "HEAD", staged=staged, use_static=use_static)
    if not results:
        return ("<div class='cs-status'>✨ No hay cambios revisables en el diff.</div>",
                render_stats_html(ReviewResult(file_path="", language="auto")),
                None,
                "Sin cambios.")
    results = [r.filter_by_severity(Severity(min_sev)) for r in results]
    md_path = _save_md_report(results)
    total = sum(len(r.findings) for r in results)
    return (
        render_findings_html(results),
        render_stats_html(results),
        md_path,
        f"✓ {len(results)} archivo(s) · {total} hallazgo(s).",
    )


# -------- UI --------


def build_ui() -> gr.Blocks:
    pulled = _client.list_models()
    model_choices = pulled if pulled else [_settings.ollama_model]
    default_model = _settings.ollama_model if _settings.ollama_model in model_choices else model_choices[0]

    theme = gr.themes.Soft(
        primary_hue="indigo",
        secondary_hue="slate",
        neutral_hue="slate",
        radius_size=gr.themes.sizes.radius_md,
        spacing_size=gr.themes.sizes.spacing_md,
    )

    with gr.Blocks(
        title="CodeSentinel AI",
        theme=theme,
        css=CSS,
        analytics_enabled=False,
    ) as demo:

        # Hero
        gr.HTML(HERO_HTML)

        # Main tabs
        with gr.Tabs(elem_id="cs-tabs"):

            # ---------- Tab 1: Paste code ----------
            with gr.Tab("Pegar código"):
                code_in = gr.Code(
                    label="Código",
                    language="python",
                    lines=16,
                    value=PASTE_PLACEHOLDER,
                )

                with gr.Row(elem_classes="cs-samples-row"):
                    sample_py = gr.Button("Bug Python", size="sm", elem_classes="cs-sample-btn")
                    sample_js = gr.Button("XSS JavaScript", size="sm", elem_classes="cs-sample-btn")
                    sample_ts = gr.Button("Tipos TypeScript", size="sm", elem_classes="cs-sample-btn")
                    sample_java = gr.Button("Legacy Java", size="sm", elem_classes="cs-sample-btn")

                paste_btn = gr.Button("Revisar código", variant="primary", size="lg")

            # ---------- Tab 2: Upload file ----------
            with gr.Tab("Subir archivo"):
                file_in = gr.File(
                    file_types=[".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".rb", ".php", ".kt", ".cpp", ".c"],
                    label="Archivo",
                )
                file_btn = gr.Button("Revisar archivo", variant="primary", size="lg")

            # ---------- Tab 3: Git diff ----------
            with gr.Tab("Git diff"):
                with gr.Row():
                    repo_in = gr.Textbox(label="Repositorio", value=str(Path.cwd()), scale=3)
                    ref_in = gr.Textbox(label="Ref", value="HEAD", scale=1)
                    staged_cb = gr.Checkbox(value=False, label="Solo staged", scale=1)
                diff_btn = gr.Button("Revisar diff", variant="primary", size="lg")

            # ---------- Tab 4: About ----------
            with gr.Tab("Acerca"):
                gr.Markdown(ABOUT_MD)

        # ---------- Status bar ----------
        status = gr.Markdown(
            "Listo.",
            elem_id="cs-status-md",
        )

        # ---------- Results section ----------
        with gr.Row(equal_height=False):
            with gr.Column(scale=2):
                findings_out = gr.HTML(value=EMPTY_STATE)

            with gr.Column(scale=1):
                counts_out = gr.HTML(
                    value=render_stats_html(ReviewResult(file_path="", language="auto"))
                )
                min_sev_dd = gr.Dropdown(
                    choices=SEVERITY_CHOICES,
                    value="info",
                    label="Severidad mínima",
                    interactive=True,
                )
                report_dl = gr.File(label="Reporte Markdown", interactive=False)

        # ---------- Advanced settings (collapsed) ----------
        with gr.Accordion("Opciones avanzadas", open=False), gr.Row():
            model_dd = gr.Dropdown(
                choices=model_choices,
                value=default_model,
                label="Modelo LLM",
            )
            lang_dd = gr.Dropdown(
                choices=LANGUAGE_CHOICES,
                value="auto",
                label="Lenguaje",
            )
            static_cb = gr.Checkbox(
                value=True,
                label="Analizadores estáticos",
            )

        # ---------- Footer ----------
        gr.HTML(FOOTER_HTML)

        # ---------- Wiring ----------
        # Sample buttons
        sample_py.click(lambda: _read_sample("python"), outputs=[code_in, lang_dd])
        sample_js.click(lambda: _read_sample("javascript"), outputs=[code_in, lang_dd])
        sample_ts.click(lambda: _read_sample("typescript"), outputs=[code_in, lang_dd])
        sample_java.click(lambda: _read_sample("java"), outputs=[code_in, lang_dd])

        # Main review handlers
        paste_btn.click(
            review_pasted_code,
            inputs=[code_in, model_dd, lang_dd, min_sev_dd, static_cb],
            outputs=[findings_out, counts_out, report_dl, status],
            queue=True,
            show_progress="full",
        )
        file_btn.click(
            review_uploaded_file,
            inputs=[file_in, model_dd, lang_dd, min_sev_dd, static_cb],
            outputs=[findings_out, counts_out, report_dl, status],
            queue=True,
            show_progress="full",
        )
        diff_btn.click(
            review_git_diff_handler,
            inputs=[repo_in, ref_in, staged_cb, model_dd, min_sev_dd, static_cb],
            outputs=[findings_out, counts_out, report_dl, status],
            queue=True,
            show_progress="full",
        )

    return demo


def main() -> None:
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
