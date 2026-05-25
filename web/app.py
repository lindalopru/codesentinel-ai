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
  <div class='cs-hero-content'>
    <div class='cs-hero-logo'>
      <svg viewBox='0 0 24 24'>
        <path d='M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z'/>
        <path d='m9 12 2 2 4-4'/>
      </svg>
    </div>
    <div>
      <h1>CodeSentinel AI</h1>
      <p>Revisor de código con IA, ejecutándose 100% en tu Mac.</p>
    </div>
  </div>
  <div class='cs-hero-meta'>
    <span class='cs-pill'>
      <span class='dot'></span>
      Local
    </span>
    <span class='cs-pill'>
      <svg viewBox='0 0 24 24'>
        <polyline points='16 18 22 12 16 6'/>
        <polyline points='8 6 2 12 8 18'/>
      </svg>
      <code>{_settings.ollama_model.split(':')[0]}</code>
    </span>
  </div>
</div>
"""

ABOUT_HTML = f"""
<div class='cs-about'>

  <section class='cs-about-section'>
    <h3 class='cs-about-title'>Cómo funciona</h3>
    <p class='cs-about-lead'>
      CodeSentinel combina un modelo de lenguaje local
      <code>Qwen2.5-Coder 7B</code> vía Ollama con analizadores estáticos clásicos
      (<code>bandit</code>, <code>ruff</code>, <code>ESLint</code>) para detectar problemas en el código.
    </p>

    <div class='cs-feature-grid'>
      <div class='cs-feature'>
        <div class='cs-feature-icon sev-critical'>
          <svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M12 9v4'/><path d='M12 17h.01'/><path d='M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z'/></svg>
        </div>
        <div>
          <div class='cs-feature-title'>Seguridad</div>
          <div class='cs-feature-body'>SQL injection · XSS · eval() · secretos hardcoded</div>
        </div>
      </div>

      <div class='cs-feature'>
        <div class='cs-feature-icon sev-high'>
          <svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='m8 2 1.88 1.88'/><path d='M14.12 3.88 16 2'/><path d='M9 7.13v-1a3.003 3.003 0 1 1 6 0v1'/><path d='M12 20c-3.3 0-6-2.7-6-6v-3a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v3c0 3.3-2.7 6-6 6'/><path d='M12 20v-9'/><path d='M6.53 9C4.6 8.8 3 7.1 3 5'/><path d='M6 13H2'/><path d='M3 21c0-2.1 1.7-3.9 3.8-4'/><path d='M20.97 5c0 2.1-1.6 3.8-3.5 4'/><path d='M22 13h-4'/><path d='M17.2 17c2.1.1 3.8 1.9 3.8 4'/></svg>
        </div>
        <div>
          <div class='cs-feature-title'>Bugs</div>
          <div class='cs-feature-body'>Default args mutables · NPE · recursos no cerrados</div>
        </div>
      </div>

      <div class='cs-feature'>
        <div class='cs-feature-icon sev-medium'>
          <svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M13 2 3 14h9l-1 8 10-12h-9l1-8z'/></svg>
        </div>
        <div>
          <div class='cs-feature-title'>Performance</div>
          <div class='cs-feature-body'>Bucles N+1 · I/O bloqueante · queries lentas</div>
        </div>
      </div>

      <div class='cs-feature'>
        <div class='cs-feature-icon sev-low'>
          <svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M12 19l7-7 3 3-7 7-3-3z'/><path d='M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z'/><path d='M2 2l7.586 7.586'/><circle cx='11' cy='11' r='2'/></svg>
        </div>
        <div>
          <div class='cs-feature-title'>Estilo</div>
          <div class='cs-feature-body'>Imports sin usar · código muerto · convenciones</div>
        </div>
      </div>

      <div class='cs-feature'>
        <div class='cs-feature-icon sev-info'>
          <svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z'/><path d='M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z'/></svg>
        </div>
        <div>
          <div class='cs-feature-title'>Documentación</div>
          <div class='cs-feature-body'>Docstrings · comentarios · API docs faltantes</div>
        </div>
      </div>
    </div>
  </section>

  <section class='cs-about-section'>
    <h3 class='cs-about-title'>Tres formas de usarlo</h3>
    <div class='cs-usage-grid'>
      <div class='cs-usage'>
        <div class='cs-usage-num'>1</div>
        <div>
          <div class='cs-usage-title'>Esta interfaz</div>
          <div class='cs-usage-body'>Lo que estás viendo. Sube archivo, pega código o revisa un diff.</div>
        </div>
      </div>
      <div class='cs-usage'>
        <div class='cs-usage-num'>2</div>
        <div>
          <div class='cs-usage-title'>Terminal</div>
          <div class='cs-usage-body'><code>codesentinel review archivo.py</code></div>
        </div>
      </div>
      <div class='cs-usage'>
        <div class='cs-usage-num'>3</div>
        <div>
          <div class='cs-usage-title'>App de escritorio</div>
          <div class='cs-usage-body'><code>make desktop</code> o doble-clic en <code>Launch_CodeSentinel.command</code></div>
        </div>
      </div>
    </div>
  </section>

  <section class='cs-about-section'>
    <div class='cs-privacy'>
      <div class='cs-privacy-icon'>
        <svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><rect width='18' height='11' x='3' y='11' rx='2'/><path d='M7 11V7a5 5 0 0 1 10 0v4'/></svg>
      </div>
      <div>
        <div class='cs-privacy-title'>100% privado</div>
        <div class='cs-privacy-body'>
          Ningún byte de tu código sale de tu Mac. La única conexión de red es
          <code>127.0.0.1:11434</code> hacia el daemon de Ollama, que corre completamente local.
        </div>
      </div>
    </div>
  </section>

  <section class='cs-about-section'>
    <h3 class='cs-about-title'>Configuración</h3>
    <div class='cs-config'>
      <div class='cs-config-row'>
        <span class='cs-config-key'>Modelo</span>
        <span class='cs-config-val'><code>{_settings.ollama_model}</code></span>
      </div>
      <div class='cs-config-row'>
        <span class='cs-config-key'>Host</span>
        <span class='cs-config-val'><code>{_settings.ollama_host}</code></span>
      </div>
      <div class='cs-config-row'>
        <span class='cs-config-key'>Context window</span>
        <span class='cs-config-val'><code>{_settings.ollama_num_ctx:,} tokens</code></span>
      </div>
      <div class='cs-config-row'>
        <span class='cs-config-key'>Versión</span>
        <span class='cs-config-val'><code>v{__version__}</code></span>
      </div>
    </div>
  </section>

  <p class='cs-about-credit'>
    Proyecto 2 de <i>Inteligencia Artificial</i> · Universidad Surcolombiana (USCO).
  </p>
</div>
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
                gr.HTML(ABOUT_HTML)

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
