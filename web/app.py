"""CodeSentinel AI — Gradio web UI, premium edition."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path

import gradio as gr

from codesentinel import __version__
from codesentinel.config import get_settings
from codesentinel.languages import EXTENSION_MAP, detect_language
from codesentinel.llm.client import OllamaClient
from codesentinel.reporting import to_markdown
from codesentinel.review import ReviewEngine
from codesentinel.schema import ReviewResult, Severity
from web.components import (
    EMPTY_STATE,
    LOADING_STATE,
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
      <p data-i18n='hero.subtitle'>Revisor de código con IA, ejecutándose 100% en tu Mac.</p>
    </div>
  </div>
  <div class='cs-hero-meta'>
    <span class='cs-pill'>
      <span class='dot'></span>
      <span data-i18n='pill.local'>Local</span>
    </span>
    <span class='cs-pill'>
      <svg viewBox='0 0 24 24'>
        <polyline points='16 18 22 12 16 6'/>
        <polyline points='8 6 2 12 8 18'/>
      </svg>
      <code>{_settings.ollama_model.split(':')[0]}</code>
    </span>
    <button id='cs-lang-toggle' class='cs-lang-toggle' type='button'
            aria-label='Switch language' title='Switch language / Cambiar idioma'>
      <svg viewBox='0 0 24 24'>
        <circle cx='12' cy='12' r='10'/>
        <path d='M2 12h20'/>
        <path d='M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z'/>
      </svg>
      <span class='lang-es'>ES</span>
      <span class='lang-en'>EN</span>
    </button>
    <button id='cs-theme-toggle' class='cs-theme-toggle' type='button'
            aria-label='Switch theme' title='Switch theme / Cambiar tema'>
      <svg class='icon-moon' viewBox='0 0 24 24'>
        <path d='M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z'/>
      </svg>
      <svg class='icon-sun' viewBox='0 0 24 24'>
        <circle cx='12' cy='12' r='4'/>
        <path d='M12 2v2'/><path d='M12 20v2'/>
        <path d='m4.93 4.93 1.41 1.41'/><path d='m17.66 17.66 1.41 1.41'/>
        <path d='M2 12h2'/><path d='M20 12h2'/>
        <path d='m6.34 17.66-1.41 1.41'/><path d='m19.07 4.93-1.41 1.41'/>
      </svg>
    </button>
  </div>
</div>
"""

ABOUT_HTML = f"""
<div class='cs-about'>

  <section class='cs-about-section'>
    <h3 class='cs-about-title' data-i18n='about.how.title'>Cómo funciona</h3>
    <p class='cs-about-lead' data-i18n='about.how.lead'>
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
          <div class='cs-feature-title' data-i18n='feature.security.title'>Seguridad</div>
          <div class='cs-feature-body' data-i18n='feature.security.body'>SQL injection · XSS · eval() · secretos hardcoded</div>
        </div>
      </div>

      <div class='cs-feature'>
        <div class='cs-feature-icon sev-high'>
          <svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='m8 2 1.88 1.88'/><path d='M14.12 3.88 16 2'/><path d='M9 7.13v-1a3.003 3.003 0 1 1 6 0v1'/><path d='M12 20c-3.3 0-6-2.7-6-6v-3a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v3c0 3.3-2.7 6-6 6'/><path d='M12 20v-9'/><path d='M6.53 9C4.6 8.8 3 7.1 3 5'/><path d='M6 13H2'/><path d='M3 21c0-2.1 1.7-3.9 3.8-4'/><path d='M20.97 5c0 2.1-1.6 3.8-3.5 4'/><path d='M22 13h-4'/><path d='M17.2 17c2.1.1 3.8 1.9 3.8 4'/></svg>
        </div>
        <div>
          <div class='cs-feature-title' data-i18n='feature.bugs.title'>Bugs</div>
          <div class='cs-feature-body' data-i18n='feature.bugs.body'>Default args mutables · NPE · recursos no cerrados</div>
        </div>
      </div>

      <div class='cs-feature'>
        <div class='cs-feature-icon sev-medium'>
          <svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M13 2 3 14h9l-1 8 10-12h-9l1-8z'/></svg>
        </div>
        <div>
          <div class='cs-feature-title' data-i18n='feature.perf.title'>Performance</div>
          <div class='cs-feature-body' data-i18n='feature.perf.body'>Bucles N+1 · I/O bloqueante · queries lentas</div>
        </div>
      </div>

      <div class='cs-feature'>
        <div class='cs-feature-icon sev-low'>
          <svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M12 19l7-7 3 3-7 7-3-3z'/><path d='M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z'/><path d='M2 2l7.586 7.586'/><circle cx='11' cy='11' r='2'/></svg>
        </div>
        <div>
          <div class='cs-feature-title' data-i18n='feature.style.title'>Estilo</div>
          <div class='cs-feature-body' data-i18n='feature.style.body'>Imports sin usar · código muerto · convenciones</div>
        </div>
      </div>

      <div class='cs-feature'>
        <div class='cs-feature-icon sev-info'>
          <svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z'/><path d='M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z'/></svg>
        </div>
        <div>
          <div class='cs-feature-title' data-i18n='feature.docs.title'>Documentación</div>
          <div class='cs-feature-body' data-i18n='feature.docs.body'>Docstrings · comentarios · API docs faltantes</div>
        </div>
      </div>
    </div>
  </section>

  <section class='cs-about-section'>
    <h3 class='cs-about-title' data-i18n='about.usage.title'>Tres formas de usarlo</h3>
    <div class='cs-usage-grid'>
      <div class='cs-usage'>
        <div class='cs-usage-num'>1</div>
        <div>
          <div class='cs-usage-title' data-i18n='usage.ui.title'>Esta interfaz</div>
          <div class='cs-usage-body' data-i18n='usage.ui.body'>Lo que estás viendo. Sube archivo, pega código o revisa un diff.</div>
        </div>
      </div>
      <div class='cs-usage'>
        <div class='cs-usage-num'>2</div>
        <div>
          <div class='cs-usage-title' data-i18n='usage.cli.title'>Terminal</div>
          <div class='cs-usage-body'><code>codesentinel review <span data-i18n='usage.cli.file'>archivo.py</span></code></div>
        </div>
      </div>
      <div class='cs-usage'>
        <div class='cs-usage-num'>3</div>
        <div>
          <div class='cs-usage-title' data-i18n='usage.desktop.title'>App de escritorio</div>
          <div class='cs-usage-body'>
            <span data-i18n='usage.desktop.run'>Ejecuta</span>
            <code>make desktop</code>
            <span data-i18n='usage.desktop.or'>o doble-clic en</span>
            <code>Launch_CodeSentinel.command</code>
          </div>
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
        <div class='cs-privacy-title' data-i18n='privacy.title'>100% privado</div>
        <div class='cs-privacy-body' data-i18n='privacy.body'>
          Ningún byte de tu código sale de tu Mac. La única conexión de red es
          <code>127.0.0.1:11434</code> hacia el daemon de Ollama, que corre completamente local.
        </div>
      </div>
    </div>
  </section>

  <section class='cs-about-section'>
    <h3 class='cs-about-title' data-i18n='about.config.title'>Configuración</h3>
    <div class='cs-config'>
      <div class='cs-config-row'>
        <span class='cs-config-key' data-i18n='config.model'>Modelo</span>
        <span class='cs-config-val'><code>{_settings.ollama_model}</code></span>
      </div>
      <div class='cs-config-row'>
        <span class='cs-config-key' data-i18n='config.host'>Host</span>
        <span class='cs-config-val'><code>{_settings.ollama_host}</code></span>
      </div>
      <div class='cs-config-row'>
        <span class='cs-config-key' data-i18n='config.ctx'>Context window</span>
        <span class='cs-config-val'><code>{_settings.ollama_num_ctx:,} tokens</code></span>
      </div>
      <div class='cs-config-row'>
        <span class='cs-config-key' data-i18n='config.version'>Versión</span>
        <span class='cs-config-val'><code>v{__version__}</code></span>
      </div>
    </div>
  </section>

  <p class='cs-about-credit'>
    <span data-i18n='about.credit'>Proyecto 2 de <i>Inteligencia Artificial</i></span>
    · Universidad Surcolombiana (USCO).
  </p>
</div>
"""

FOOTER_HTML = f"""
<div class='cs-footer'>
  <b>Linda Valentina Lopez Rubiano</b> &middot; <b>Juan Felipe Andrade</b>
  &middot; <span data-i18n='footer.university'>USCO</span>
  &middot; v{__version__}
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


DOWNLOADS_DIR = Path.home() / "Downloads"


def _save_md_report(results: ReviewResult | list[ReviewResult]) -> str:
    """Write the report directly into the user's Downloads folder so they
    find it instantly in Finder. Returns the path so Gradio's file output
    can also offer it as a download link."""
    md = to_markdown(results)
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = DOWNLOADS_DIR / f"CodeSentinel_report_{ts}.md"
    out.write_text(md, encoding="utf-8")
    return str(out)


def _empty_outputs():
    return (
        EMPTY_STATE,
        render_stats_html(ReviewResult(file_path="", language="auto")),
        None,
        "Listo.",
    )


# -------- handlers --------


def _empty_stats():
    return render_stats_html(ReviewResult(file_path="", language="auto"))


def _loading_status() -> str:
    """Loading state HTML — a CSS-animated spinner next to a status string.
    Both pieces are translatable via data-i18n."""
    return (
        "<div class='cs-status-line cs-status-loading'>"
        "<span class='cs-status-spinner'></span>"
        "<span data-i18n='status.reviewing'>Revisando código…</span>"
        "</div>"
    )


def _status_done(text: str, *, md_path: str | None = None) -> str:
    """Render the 'done' status with an optional 'Saved to ~/Downloads/…' link."""
    saved_html = ""
    if md_path:
        fname = Path(md_path).name
        saved_html = (
            "<span class='cs-status-saved'>"
            "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' "
            "stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
            "<path d='M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'/>"
            "<polyline points='7 10 12 15 17 10'/>"
            "<line x1='12' y1='15' x2='12' y2='3'/></svg> "
            f"<span data-i18n='status.saved'>Guardado en</span> "
            f"<code>~/Downloads/{fname}</code>"
            "</span>"
        )
    return f"<div class='cs-status-line cs-status-done'>{text}{saved_html}</div>"


def _norm_lang(v: str) -> str:
    """Normalise the hidden output-language textbox value to 'en' or 'es'."""
    s = (v or "es").strip().lower()
    return "en" if s.startswith("en") else "es"


def _resolve_uploaded_path(file_obj) -> Path:
    """Gradio 5's gr.File can return different shapes (NamedString, str,
    dict with `.path`, FileData). Normalise to a real Path."""
    if file_obj is None:
        raise ValueError("file_obj is None")
    if isinstance(file_obj, str):
        return Path(file_obj)
    # Most common: NamedString or _TemporaryFileWrapper with .name
    name = getattr(file_obj, "name", None)
    if isinstance(name, str) and name:
        return Path(name)
    # FileData dict { 'path': ..., 'orig_name': ..., 'meta': {...} }
    if isinstance(file_obj, dict):
        for k in ("path", "name", "orig_name"):
            if file_obj.get(k):
                return Path(file_obj[k])
    raise ValueError(f"Unrecognised file_obj type: {type(file_obj).__name__}")


def review_uploaded_file(
    file_obj, model: str, language: str, min_sev: str, use_static: bool, out_lang: str,
):
    if file_obj is None:
        yield ("<div class='cs-status'>⬆️ Sube un archivo para empezar.</div>",
               _empty_stats(), None, _status_done("Listo."))
        return

    # Resolve the file path robustly. Surface any error clearly.
    try:
        path = _resolve_uploaded_path(file_obj)
    except Exception as exc:
        yield (f"<div class='cs-status'>❌ No pude leer el archivo: {exc}</div>",
               _empty_stats(), None, _status_done("Error."))
        return

    if not path.exists() or path.stat().st_size == 0:
        yield (f"<div class='cs-status'>❌ El archivo está vacío o no existe ({path}).</div>",
               _empty_stats(), None, _status_done("Error."))
        return

    # Loading state — yields immediately so the UI shows a spinner.
    yield (LOADING_STATE, _empty_stats(), None, _loading_status())

    engine = _resolve_engine(model)
    detected = detect_language(path)

    # Static analyzers only apply to languages they understand.
    can_static = use_static and detected in {"python", "javascript", "typescript"}

    try:
        result = engine.review_file(
            path, use_static=can_static, output_language=_norm_lang(out_lang),
        )
    except Exception as exc:
        yield (f"<div class='cs-status'>❌ Error durante el análisis: {exc}</div>",
               _empty_stats(), None, _status_done("Error."))
        return

    # Show just the filename, not Gradio's ugly tempfile path.
    result.file_path = path.name

    # If detection failed AND the user picked a specific language, honour it.
    if result.language == "unknown" and language and language != "auto":
        result.language = language

    result = result.filter_by_severity(Severity(min_sev))
    md_path = _save_md_report(result)
    n = len(result.findings)
    yield (
        render_findings_html(result),
        render_stats_html(result),
        md_path,
        _status_done(
            f"<b>✓</b> Revisado en {result.duration_s:.1f}s · {n} hallazgo(s).",
            md_path=md_path,
        ),
    )


_PASTE_LANG_HINTS: dict[str, tuple[str, ...]] = {
    "python":     ("def ", "import ", "print(", "from ", "self.", "#"),
    "javascript": ("function ", "const ", "let ", "var ", "=>", "require(", "//"),
    "typescript": ("interface ", ": string", ": number", ": any", "type ", "as const"),
    "java":       ("public class", "public static", "import java", "@Override", "System.out"),
    "go":         ("package ", "func ", "import (", "fmt.", ":= ", "go func"),
    "rust":       ("fn ", "let mut ", "pub fn", "use std::", "impl ", "->"),
    "ruby":       ("def ", "end", "require '", "puts ", "@"),
    "php":        ("<?php", "function ", "$this->", "echo "),
}


def _sniff_language(code: str) -> str:
    """Detect language from pasted code by counting tell-tale tokens."""
    head = code[:2000]
    best, best_hits = "python", 0
    for lang, hints in _PASTE_LANG_HINTS.items():
        hits = sum(1 for h in hints if h in head)
        if hits > best_hits:
            best, best_hits = lang, hits
    return best if best_hits >= 2 else "python"


def review_pasted_code(
    code: str, model: str, language: str, min_sev: str, use_static: bool, out_lang: str,
):
    if not code or not code.strip():
        yield ("<div class='cs-status'>📝 Pega código o usa un ejemplo de arriba.</div>",
               _empty_stats(), None, _status_done("Listo."))
        return
    yield (LOADING_STATE, _empty_stats(), None, _loading_status())

    # Resolve language: explicit user choice wins; otherwise sniff from code.
    lang = language if language and language != "auto" else _sniff_language(code)

    out = _norm_lang(out_lang)
    engine = _resolve_engine(model)

    # Static analyzers only understand python (bandit, ruff) and js/ts (eslint).
    # Running ruff on Go produces 46 fake "invalid-syntax" errors — disable.
    can_static = use_static and lang in {"python", "javascript", "typescript"}

    if can_static:
        ext = next((e for e, name in EXTENSION_MAP.items() if name == lang), ".txt")
        tmp = Path(tempfile.mkdtemp()) / f"pasted{ext}"
        tmp.write_text(code, encoding="utf-8")
        try:
            result = engine.review_file(tmp, use_static=True, output_language=out)
        except Exception as exc:
            yield (f"<div class='cs-status'>❌ Error durante el análisis: {exc}</div>",
                   _empty_stats(), None, _status_done("Error."))
            return
        result.file_path = "pasted snippet"
    else:
        try:
            result = engine.review_source(
                code, language=lang, file_path="pasted snippet",
                use_static=False, output_language=out,
            )
        except Exception as exc:
            yield (f"<div class='cs-status'>❌ Error durante el análisis: {exc}</div>",
                   _empty_stats(), None, _status_done("Error."))
            return

    result = result.filter_by_severity(Severity(min_sev))
    md_path = _save_md_report(result)
    n = len(result.findings)
    yield (
        render_findings_html(result),
        render_stats_html(result),
        md_path,
        _status_done(
            f"<b>✓</b> Revisado en {result.duration_s:.1f}s · {n} hallazgo(s).",
            md_path=md_path,
        ),
    )


def review_git_diff_handler(
    repo_path: str, ref: str, staged: bool, model: str, min_sev: str, use_static: bool, out_lang: str,
):
    if not repo_path or not Path(repo_path).exists():
        yield ("<div class='cs-status'>📁 Provee la ruta a un repositorio git válido.</div>",
               _empty_stats(), None, _status_done("Listo."))
        return
    yield (LOADING_STATE, _empty_stats(), None, _loading_status())

    engine = _resolve_engine(model)
    results = engine.review_diff(
        Path(repo_path), ref=ref or "HEAD", staged=staged, use_static=use_static,
        output_language=_norm_lang(out_lang),
    )
    if not results:
        yield ("<div class='cs-status'>✨ No hay cambios revisables en el diff.</div>",
               _empty_stats(), None, _status_done("Sin cambios."))
        return
    results = [r.filter_by_severity(Severity(min_sev)) for r in results]
    md_path = _save_md_report(results)
    total = sum(len(r.findings) for r in results)
    yield (
        render_findings_html(results),
        render_stats_html(results),
        md_path,
        _status_done(
            f"<b>✓</b> {len(results)} archivo(s) · {total} hallazgo(s).",
            md_path=md_path,
        ),
    )


# -------- UI --------


def build_ui() -> gr.Blocks:
    pulled = _client.list_models()
    model_choices = pulled if pulled else [_settings.ollama_model]
    default_model = _settings.ollama_model if _settings.ollama_model in model_choices else model_choices[0]

    # Use Base theme — it's the lightest preset and lets our CSS take over fully.
    # Soft / Default both ship dark variants for some components (dropdowns,
    # accordion) that our `color-scheme: light` can't override cleanly.
    theme = gr.themes.Base(
        primary_hue="indigo",
        secondary_hue="indigo",
        neutral_hue="zinc",
        radius_size=gr.themes.sizes.radius_md,
        spacing_size=gr.themes.sizes.spacing_md,
        font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
    )

    # JavaScript handles theme + language switching. Runs once on page load.
    theme_js = r"""
() => {
  /* =================================================================
   *  Translation dictionary.  Spanish is the source of truth — DOM
   *  contains Spanish text. English translations are stored here.
   * ================================================================= */
  const STRINGS = {
    /* hero + chrome */
    'hero.subtitle':    { es: 'Revisor de código con IA, ejecutándose 100% en tu Mac.',
                          en: 'AI code reviewer, running 100% on your Mac.' },
    'pill.local':       { es: 'Local',                   en: 'Local' },
    'footer.university':{ es: 'USCO',                    en: 'USCO' },

    /* about — how */
    'about.how.title':  { es: 'Cómo funciona',           en: 'How it works' },
    'about.how.lead':   { es: 'CodeSentinel combina un modelo de lenguaje local <code>Qwen2.5-Coder 7B</code> vía Ollama con analizadores estáticos clásicos (<code>bandit</code>, <code>ruff</code>, <code>ESLint</code>) para detectar problemas en el código.',
                          en: 'CodeSentinel pairs a local <code>Qwen2.5-Coder 7B</code> model via Ollama with classic static analysers (<code>bandit</code>, <code>ruff</code>, <code>ESLint</code>) to surface problems in your code.' },

    /* about — features */
    'feature.security.title': { es: 'Seguridad',         en: 'Security' },
    'feature.security.body':  { es: 'SQL injection · XSS · eval() · secretos hardcoded',
                                en: 'SQL injection · XSS · eval() · hardcoded secrets' },
    'feature.bugs.title':     { es: 'Bugs',              en: 'Bugs' },
    'feature.bugs.body':      { es: 'Default args mutables · NPE · recursos no cerrados',
                                en: 'Mutable default args · NPE · unclosed resources' },
    'feature.perf.title':     { es: 'Performance',       en: 'Performance' },
    'feature.perf.body':      { es: 'Bucles N+1 · I/O bloqueante · queries lentas',
                                en: 'N+1 loops · blocking I/O · slow queries' },
    'feature.style.title':    { es: 'Estilo',            en: 'Style' },
    'feature.style.body':     { es: 'Imports sin usar · código muerto · convenciones',
                                en: 'Unused imports · dead code · conventions' },
    'feature.docs.title':     { es: 'Documentación',     en: 'Documentation' },
    'feature.docs.body':      { es: 'Docstrings · comentarios · API docs faltantes',
                                en: 'Docstrings · comments · missing API docs' },

    /* about — usage */
    'about.usage.title':      { es: 'Tres formas de usarlo',    en: 'Three ways to use it' },
    'usage.ui.title':         { es: 'Esta interfaz',            en: 'This interface' },
    'usage.ui.body':          { es: 'Lo que estás viendo. Sube archivo, pega código o revisa un diff.',
                                en: 'What you are looking at. Upload a file, paste code, or review a diff.' },
    'usage.cli.title':        { es: 'Terminal',                 en: 'Terminal' },
    'usage.cli.file':         { es: 'archivo.py',               en: 'file.py' },
    'usage.desktop.title':    { es: 'App de escritorio',        en: 'Desktop app' },
    'usage.desktop.run':      { es: 'Ejecuta',                  en: 'Run' },
    'usage.desktop.or':       { es: 'o doble-clic en',          en: 'or double-click' },

    /* about — privacy + config */
    'privacy.title':          { es: '100% privado',             en: '100% private' },
    'privacy.body':           { es: 'Ningún byte de tu código sale de tu Mac. La única conexión de red es <code>127.0.0.1:11434</code> hacia el daemon de Ollama, que corre completamente local.',
                                en: 'Not a single byte of your code leaves your Mac. The only network connection is <code>127.0.0.1:11434</code> to the Ollama daemon, running fully on-device.' },
    'about.config.title':     { es: 'Configuración',            en: 'Configuration' },
    'config.model':           { es: 'Modelo',                   en: 'Model' },
    'config.host':            { es: 'Host',                     en: 'Host' },
    'config.ctx':             { es: 'Context window',           en: 'Context window' },
    'config.version':         { es: 'Versión',                  en: 'Version' },
    'about.credit':           { es: 'Proyecto 2 de <i>Inteligencia Artificial</i>',
                                en: 'Project 2 of <i>Artificial Intelligence</i>' },

    /* empty / success states */
    'empty.title':            { es: 'Sin análisis aún',         en: 'No analysis yet' },
    'empty.body':             { es: 'Pega código, sube un archivo o prueba un ejemplo para empezar.',
                                en: 'Paste code, upload a file, or try a sample to get started.' },
    'no_findings.title':      { es: 'Sin hallazgos',            en: 'No issues found' },
    'no_findings.body':       { es: 'El modelo no detectó problemas en el código revisado.',
                                en: 'The model did not detect any problems in the reviewed code.' },

    /* finding card chrome */
    'finding.suggestion':     { es: 'Sugerencia:',              en: 'Suggestion:' },

    /* loading + status */
    'status.ready':           { es: 'Listo.',                   en: 'Ready.' },
    'status.reviewing':       { es: 'Revisando código…',        en: 'Reviewing code…' },
    'status.saved':           { es: 'Guardado en',              en: 'Saved to' },
    'loading.title':          { es: 'Analizando código…',       en: 'Analyzing code…' },
    'loading.body':           { es: 'El modelo está revisando tu código. Esto puede tardar 10–60 segundos.',
                                en: 'The model is analyzing your code. This may take 10–60 seconds.' },

    /* toast notifications */
    'toast.download.title':   { es: 'Descarga iniciada',
                                en: 'Download started' },
    'toast.download.body':    { es: 'El reporte también está guardado en tu carpeta Descargas.',
                                en: 'The report is also saved to your Downloads folder.' },
    'toast.saved.title':      { es: 'Reporte guardado',
                                en: 'Report saved' },
    'toast.saved.body':       { es: 'Encuéntralo en tu carpeta Descargas.',
                                en: 'Find it in your Downloads folder.' },
  };

  /* =================================================================
   *  Gradio components don't accept data-i18n attributes for their
   *  built-in labels (tab text, button text, form labels). For those
   *  we match by exact Spanish text and swap to English (and back).
   *  Keep both directions so the user can flip multiple times.
   * ================================================================= */
  const GRADIO_LABELS = {
    /* Tabs */
    'Pegar código':              'Paste code',
    'Subir archivo':             'Upload file',
    'Git diff':                  'Git diff',
    'Acerca':                    'About',
    /* Buttons */
    'Revisar código':            'Review code',
    'Revisar archivo':           'Review file',
    'Revisar diff':              'Review diff',
    /* Sample chips */
    'Bug Python':                'Python bug',
    'XSS JavaScript':            'JS XSS',
    'Tipos TypeScript':          'TS types',
    'Legacy Java':               'Legacy Java',
    /* Form labels */
    'Código':                    'Code',
    'Archivo':                   'File',
    'Repositorio':               'Repository',
    'Ref':                       'Ref',
    'Solo staged':               'Staged only',
    'Severidad mínima':          'Min severity',
    'Reporte Markdown':          'Markdown report',
    'Opciones avanzadas':        'Advanced options',
    'Modelo LLM':                'LLM Model',
    'Lenguaje':                  'Language',
    'Analizadores estáticos':    'Static analyzers',
    /* Status copy */
    'Listo.':                    'Ready.',
    'Prueba con un ejemplo:':    'Try a sample:',
  };

  /* =================================================================
   *  Status-message patterns from review handlers — regex-based since
   *  they include numbers ("✓ Revisado en 8.3s · 2 hallazgo(s).").
   * ================================================================= */
  const STATUS_PATTERNS = [
    { es: /Revisado en/g,           en: 'Reviewed in' },
    { es: /hallazgo\(s\)\./g,       en: 'finding(s).' },
    { es: /hallazgo\(s\)/g,         en: 'finding(s)' },
    { es: /archivo\(s\)/g,          en: 'file(s)' },
    { es: /Sin cambios\./g,         en: 'No changes.' },
    { es: /No hay cambios revisables en el diff\./g,
                                    en: 'No reviewable changes in the diff.' },
    { es: /Pega código o usa un ejemplo de arriba\./g,
                                    en: 'Paste code or use a sample above.' },
    { es: /Sube un archivo para empezar\./g,
                                    en: 'Upload a file to begin.' },
    { es: /Provee la ruta a un repositorio git válido\./g,
                                    en: 'Provide a valid git repository path.' },
  ];

  /* =================================================================
   *  Theme system
   * ================================================================= */
  const T_KEY = 'cs-theme';
  const applyTheme = (t) => document.documentElement.setAttribute('data-theme', t);
  let savedTheme = null;
  try { savedTheme = localStorage.getItem(T_KEY); } catch (e) {}
  if (!savedTheme) {
    savedTheme = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)
      ? 'dark' : 'light';
  }
  applyTheme(savedTheme);

  /* =================================================================
   *  Language system
   * ================================================================= */
  const L_KEY = 'cs-lang';
  let lang = 'es';
  try { lang = localStorage.getItem(L_KEY) || 'es'; } catch (e) {}

  const applyI18nElements = () => {
    document.querySelectorAll('[data-i18n]').forEach((el) => {
      const key = el.getAttribute('data-i18n');
      const entry = STRINGS[key];
      if (!entry) return;
      const text = entry[lang];
      if (text === undefined) return;
      /* Avoid clobbering nested elements we don't control — only set if
       * the element's data-i18n key drives its full textual content. */
      if (text.includes('<')) {
        el.innerHTML = text;
      } else {
        el.textContent = text;
      }
    });
  };

  /* Walk Gradio component labels and swap by exact text match.
   * Direction depends on current `lang`. */
  const applyGradioLabels = (root) => {
    root = root || document.body;
    /* Tab buttons */
    root.querySelectorAll('button[role="tab"], .tab-nav button').forEach((el) => {
      const t = (el.textContent || '').trim();
      const fwd = GRADIO_LABELS[t];
      if (lang === 'en' && fwd) { el.textContent = fwd; return; }
      const rev = Object.keys(GRADIO_LABELS).find(k => GRADIO_LABELS[k] === t);
      if (lang === 'es' && rev) el.textContent = rev;
    });
    /* Form labels and other static text — scope to known label containers
     * so we don't accidentally translate user-pasted code. */
    const selectors = [
      'label', '.block-label', '[class*="block-label"]',
      '.gr-button', 'button',
      'summary', '[class*="accordion"] > button',
      '.cs-samples-row button',
    ];
    selectors.forEach((sel) => {
      root.querySelectorAll(sel).forEach((el) => {
        /* Skip our toggle buttons and elements with data-i18n (handled separately) */
        if (el.id === 'cs-theme-toggle' || el.id === 'cs-lang-toggle') return;
        if (el.hasAttribute('data-i18n')) return;
        /* Only translate if the element has direct text (no child elements that
         * carry their own state, like icons). */
        const directText = Array.from(el.childNodes)
          .filter(n => n.nodeType === 3)
          .map(n => n.textContent.trim())
          .join(' ').trim();
        if (!directText) return;
        const fwd = GRADIO_LABELS[directText];
        if (lang === 'en' && fwd) {
          replaceDirectText(el, fwd); return;
        }
        const rev = Object.keys(GRADIO_LABELS).find(k => GRADIO_LABELS[k] === directText);
        if (lang === 'es' && rev) replaceDirectText(el, rev);
      });
    });
    /* CSS pseudo-element for "Prueba con un ejemplo:" — handled via CSS var */
    document.documentElement.style.setProperty(
      '--cs-samples-label',
      lang === 'en' ? '"Try a sample:"' : '"Prueba con un ejemplo:"'
    );
  };

  const replaceDirectText = (el, newText) => {
    /* Replace only the first text node, preserve children */
    for (const n of el.childNodes) {
      if (n.nodeType === 3 && n.textContent.trim()) {
        n.textContent = ' ' + newText + ' ';
        return;
      }
    }
    /* Fallback: append a text node */
    el.appendChild(document.createTextNode(' ' + newText + ' '));
  };

  /* Translate status markdown (look for our specific patterns) */
  const applyStatus = () => {
    const md = document.getElementById('cs-status-md');
    if (!md) return;
    let txt = md.textContent || '';
    if (lang === 'en') {
      STATUS_PATTERNS.forEach(p => { txt = txt.replace(p.es, p.en); });
    }
    /* Don't double-apply if no change needed */
    if (txt !== md.textContent) {
      md.textContent = txt;
    }
  };

  /* Push the active language into the Gradio dropdown for output-language
   * so review handlers know what language to ask the LLM for. The dropdown
   * lives in advanced options (visible) so the user can also override it
   * manually. Retries until the element exists since Gradio renders async. */
  let _syncAttempts = 0;
  const syncOutputLang = () => {
    const root = document.getElementById('cs-output-lang');
    if (!root) {
      if (_syncAttempts++ < 40) setTimeout(syncOutputLang, 100);
      return;
    }
    /* Gradio Dropdown has a child input that holds the current value */
    const input = root.querySelector('input, textarea, select');
    if (!input) {
      if (_syncAttempts++ < 40) setTimeout(syncOutputLang, 100);
      return;
    }
    if (input.value !== lang) {
      const proto = input.tagName === 'TEXTAREA'
        ? HTMLTextAreaElement.prototype
        : (input.tagName === 'SELECT' ? HTMLSelectElement.prototype : HTMLInputElement.prototype);
      const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
      setter.call(input, lang);
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
      /* For dropdowns, also click any matching option in the open list */
      const opts = root.querySelectorAll('[role="option"], .item');
      opts.forEach(o => {
        if ((o.textContent || '').trim() === lang) {
          o.setAttribute('aria-selected', 'true');
        }
      });
    }
  };

  /* =================================================================
   *  Toast / snackbar — declared early so applyAll can call it
   * ================================================================= */
  let _toastContainer = null;
  function showToast(titleKey, bodyKey, filename) {
    if (!_toastContainer) {
      _toastContainer = document.createElement('div');
      _toastContainer.className = 'cs-toast-container';
      document.body.appendChild(_toastContainer);
    }
    const t = (STRINGS[titleKey] && STRINGS[titleKey][lang]) || titleKey;
    const b = (STRINGS[bodyKey]  && STRINGS[bodyKey][lang])  || bodyKey;
    const safeName = (filename || '').replace(/[<>]/g, '');
    const fnameHtml = safeName ? `<br/><code>~/Downloads/${safeName}</code>` : '';
    const toast = document.createElement('div');
    toast.className = 'cs-toast';
    toast.innerHTML = `
      <div class='cs-toast-icon'>
        <svg viewBox='0 0 24 24'><polyline points='20 6 9 17 4 12'/></svg>
      </div>
      <div class='cs-toast-text'>
        <strong>${t}</strong>
        <small>${b}${fnameHtml}</small>
      </div>
      <button class='cs-toast-close' type='button' aria-label='Close'>
        <svg viewBox='0 0 24 24'><line x1='18' y1='6' x2='6' y2='18'/><line x1='6' y1='6' x2='18' y2='18'/></svg>
      </button>
    `;
    _toastContainer.appendChild(toast);
    const remove = () => {
      toast.classList.add('cs-toast-leaving');
      setTimeout(() => toast.remove(), 280);
    };
    toast.querySelector('.cs-toast-close').addEventListener('click', remove);
    setTimeout(remove, 4500);
  }

  function wireDownloads(root) {
    root = root || document.body;
    /* gr.File download link */
    root.querySelectorAll('[data-testid="file"] a, .gr-file a, [class*="file-preview"] a, [id*="report"] a').forEach((a) => {
      if (a.dataset.csToastBound) return;
      a.dataset.csToastBound = '1';
      a.addEventListener('click', () => {
        const href = a.getAttribute('href') || '';
        const fname = (href.split('?')[0] || '').split('/').pop() || '';
        showToast('toast.download.title', 'toast.download.body', fname);
      });
    });
    /* Status "Guardado en …" pill */
    root.querySelectorAll('.cs-status-saved').forEach((el) => {
      if (el.dataset.csToastBound) return;
      el.dataset.csToastBound = '1';
      el.addEventListener('click', () => {
        const code = el.querySelector('code');
        const fname = code ? (code.textContent || '').replace(/^~\/Downloads\//, '').trim() : '';
        showToast('toast.saved.title', 'toast.saved.body', fname);
      });
    });
  }

  const applyAll = () => {
    document.documentElement.setAttribute('data-lang', lang);
    applyI18nElements();
    applyGradioLabels();
    applyStatus();
    syncOutputLang();
    wireDownloads();
  };

  /* =================================================================
   *  Wire toggle buttons (retry until they exist — Gradio renders async)
   * ================================================================= */
  const attach = () => {
    const themeBtn = document.getElementById('cs-theme-toggle');
    const langBtn  = document.getElementById('cs-lang-toggle');
    let bound = true;

    if (themeBtn && !themeBtn.dataset.bound) {
      themeBtn.dataset.bound = '1';
      themeBtn.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme') || 'light';
        const next = current === 'dark' ? 'light' : 'dark';
        applyTheme(next);
        try { localStorage.setItem(T_KEY, next); } catch (e) {}
      });
    } else if (!themeBtn) { bound = false; }

    if (langBtn && !langBtn.dataset.bound) {
      langBtn.dataset.bound = '1';
      langBtn.addEventListener('click', () => {
        lang = (lang === 'es') ? 'en' : 'es';
        try { localStorage.setItem(L_KEY, lang); } catch (e) {}
        /* Stale findings were generated in the OLD language. Reset the
         * results panel so the user re-runs in the new language. */
        const findingsEl = document.getElementById('cs-findings-out');
        const countsEl = document.getElementById('cs-counts-out');
        const statusEl = document.getElementById('cs-status-md');
        const emptyHTML = (lang === 'es')
          ? `<div class='cs-empty'><div class='ico'><svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'><circle cx='11' cy='11' r='8'/><path d='m21 21-4.3-4.3'/></svg></div><h3>Sin análisis aún</h3><p>Pega código, sube un archivo o prueba un ejemplo para empezar.</p></div>`
          : `<div class='cs-empty'><div class='ico'><svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'><circle cx='11' cy='11' r='8'/><path d='m21 21-4.3-4.3'/></svg></div><h3>No analysis yet</h3><p>Paste code, upload a file, or try a sample to get started.</p></div>`;
        const zeroStats = `<div class='cs-stats-grid'>` +
          ['critical','high','medium','low','info'].map(s =>
            `<div class='cs-stat-card ${s} zero'><div class='v'>0</div><div class='l'>${s}</div></div>`).join('') +
          `</div>`;
        const readyTxt = (lang === 'es') ? 'Listo.' : 'Ready.';
        if (findingsEl) findingsEl.innerHTML = emptyHTML;
        if (countsEl)   countsEl.innerHTML   = zeroStats;
        if (statusEl)   statusEl.innerHTML   = `<div class='cs-status-line'>${readyTxt}</div>`;
        applyAll();
      });
    } else if (!langBtn) { bound = false; }

    if (!bound) setTimeout(attach, 80);
  };
  attach();

  /* =================================================================
   *  MutationObserver — re-translate when Gradio rerenders findings
   *  cards or status after a review.
   * ================================================================= */
  const observer = new MutationObserver((mutations) => {
    let needsApply = false;
    for (const m of mutations) {
      if (m.addedNodes && m.addedNodes.length) {
        for (const n of m.addedNodes) {
          if (n.nodeType === 1) { needsApply = true; break; }
        }
      }
      if (needsApply) break;
    }
    if (needsApply) {
      /* Debounce a hair to let Gradio finish the batch */
      clearTimeout(observer._t);
      observer._t = setTimeout(applyAll, 50);
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
}
"""

    with gr.Blocks(
        title="CodeSentinel AI",
        theme=theme,
        css=CSS,
        js=theme_js,
        analytics_enabled=False,
        # Allow Gradio's file component to serve files from ~/Downloads so
        # the user can click to re-download from the UI.
        # Per Gradio docs the path must exist; we mkdir on app init.
        # We don't expose anything else.
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
        # HTML (not Markdown) so we can inject a CSS-animated spinner
        # during the loading state.
        status = gr.HTML(
            value="<div class='cs-status-line' data-i18n='status.ready'>Listo.</div>",
            elem_id="cs-status-md",
        )

        # ---------- Results section ----------
        with gr.Row(equal_height=False):
            with gr.Column(scale=2):
                findings_out = gr.HTML(value=EMPTY_STATE, elem_id="cs-findings-out")

            with gr.Column(scale=1):
                counts_out = gr.HTML(
                    value=render_stats_html(ReviewResult(file_path="", language="auto")),
                    elem_id="cs-counts-out",
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
                label="Lenguaje (al pegar)",
                info="Para uploads se autodetecta del archivo",
            )
            out_lang_tb = gr.Dropdown(
                choices=["es", "en"],
                value="es",
                label="Idioma de resultados",
                elem_id="cs-output-lang",
                interactive=True,
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
        # show_progress="hidden" — we render our own clean loading state
        # via the generator yield in each handler.
        paste_btn.click(
            review_pasted_code,
            inputs=[code_in, model_dd, lang_dd, min_sev_dd, static_cb, out_lang_tb],
            outputs=[findings_out, counts_out, report_dl, status],
            queue=True,
            show_progress="hidden",
        )
        file_btn.click(
            review_uploaded_file,
            inputs=[file_in, model_dd, lang_dd, min_sev_dd, static_cb, out_lang_tb],
            outputs=[findings_out, counts_out, report_dl, status],
            queue=True,
            show_progress="hidden",
        )
        diff_btn.click(
            review_git_diff_handler,
            inputs=[repo_in, ref_in, staged_cb, model_dd, min_sev_dd, static_cb, out_lang_tb],
            outputs=[findings_out, counts_out, report_dl, status],
            queue=True,
            show_progress="hidden",
        )

    return demo


def main() -> None:
    # Privacy: never phone home — this is a local-first tool.
    os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

    # Make sure ~/Downloads exists so report writes don't fail.
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    demo = build_ui()
    host = os.environ.get("CODESENTINEL_WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("CODESENTINEL_WEB_PORT", "7860"))
    demo.queue(default_concurrency_limit=1).launch(
        server_name=host,
        server_port=port,
        inbrowser=False,
        share=False,
        # Allow the gr.File output to serve files we wrote into ~/Downloads.
        allowed_paths=[str(DOWNLOADS_DIR)],
    )


if __name__ == "__main__":
    main()
