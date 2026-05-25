# Presentation script — 10-minute live demo

A script for the in-class defence of CodeSentinel AI. Times are budget targets; over- or under-running by 30 seconds is fine.

---

## 0:00 — Intro (60 s)

> "Buenas tardes profesor. Soy Linda. Este es **CodeSentinel AI**, mi Proyecto 2 de la materia.
> Es un revisor de código que usa inteligencia artificial — pero a diferencia de Copilot o CodeRabbit, **corre completo en mi laptop**.
> Ningún byte de código sale de mi máquina."

Show the project README on screen.

---

## 1:00 — The problem (45 s)

> "El problema: los revisores de código en la nube son rápidos y precisos, pero suben el código fuente a un servidor de terceros. Eso es un riesgo de privacidad y un costo recurrente. Yo quería ver si podía obtener calidad comparable usando un modelo local."

Show the comparison table from [01_report.md](01_report.md) §5.

---

## 1:45 — Architecture in 30 seconds (60 s)

> "La arquitectura tiene tres capas. **Capa uno**: Ollama corre un modelo de 7 mil millones de parámetros, Qwen2.5-Coder, totalmente en mi GPU Metal — son 4.7 GB en disco.
> **Capa dos**: el motor de revisión combina el modelo con analizadores clásicos como bandit y ruff. Los hallazgos del modelo y los analizadores se fusionan y deduplican.
> **Capa tres**: hay dos formas de manejarlo — una CLI en la terminal con Typer y Rich, y una interfaz web con Gradio."

Show the Mermaid diagram from [03_architecture.md](03_architecture.md).

---

## 2:45 — Demo: CLI on a buggy file (2 min 30 s)

```bash
make demo
```

> "Voy a correr `make demo`. Esto ejecuta CodeSentinel sobre cuatro archivos que metí intencionalmente con bugs."

Narrate while it runs:
- "Está cargando Qwen2.5-Coder en GPU — primera llamada tarda más, las siguientes son rápidas."
- Point to the first finding: "Aquí detecta inyección SQL como CRÍTICA — eso es lo que esperamos."
- "Después detecta uso de `eval` en input no confiable, también crítica."
- "Aquí está el argumento default mutable — un bug clásico de Python que rompe entre llamadas."
- "Estos otros vienen de bandit y ruff, los analizadores estáticos — el sistema los integra como hallazgos adicionales."

Total: 8 bugs intencionalmente plantados, 8 detectados, más extras.

---

## 5:15 — Demo: web UI (2 min)

```bash
make web
```

Open <http://127.0.0.1:7860>.

> "Mismo motor, pero ahora con UI web. Voy a pegar código directamente."

- Paste `examples/insecure_js.js` into the **Paste code** tab.
- Click Review.
- Show findings rendered as colour-coded cards with severity badges.
- Switch the **Min severity** dropdown to `high` — show how findings filter live.
- Click **Download Markdown report** — open the file to show structured output.

---

## 7:15 — Show robustness (60 s)

> "Tres detalles técnicos que cuestan tiempo de implementar pero importan:"

1. **Robust JSON parsing**: open [`codesentinel/llm/parser.py`](../codesentinel/llm/parser.py).
   > "El modelo a veces devuelve JSON con markdown fences, trailing commas, o prefijos de prosa. Tengo un fallback chain con cinco estrategias para extraer el JSON sin que el sistema crashee."

2. **Severity override**: open [`docs/05_prompt_engineering.md`](05_prompt_engineering.md) §"Augmentation block".
   > "Cuando bandit dice MEDIUM, mi prompt le dice al LLM que use su propio criterio. Por eso SQL injection sube a CRITICAL aunque bandit lo marque MEDIUM."

3. **Static + LLM merge**: open [`codesentinel/review/merger.py`](../codesentinel/review/merger.py).
   > "El merger usa rapidfuzz para deduplicar hallazgos similares y siempre se queda con la severidad mayor."

---

## 8:15 — Tests + coverage (45 s)

```bash
make test
```

> "55 tests, 70% de cobertura global, 95-100% en los módulos críticos (parser, schema, merger, prompts). Los analizadores tienen menos cobertura porque shell-out a subprocesos."

---

## 9:00 — Limitations + future (60 s)

Open [`docs/08_limitations.md`](08_limitations.md) briefly:

> "Tres limitaciones importantes: solo ve un archivo a la vez (no cross-file), un modelo de 7B captura menos bugs sutiles que uno de 70B, y el tiempo de carga en frío son ~55 segundos."

Open [`docs/09_future_work.md`](09_future_work.md):

> "Siguiente paso: AST-aware chunking, contexto cross-file con tree-sitter, y una extensión de VS Code que use el output SARIF que ya genero."

---

## 10:00 — Close (30 s)

> "En resumen: un revisor de código de calidad comparable a productos comerciales en la nube, corriendo 100% local, en mi MacBook Pro. MIT license. Repositorio listo para que cualquiera lo clone y `bash setup.sh`. Gracias."

Take questions.

---

## Backup answers (likely Q&A)

- **¿Por qué Qwen y no Llama?** Mejor HumanEval en 7B; entrenado más en JSON; license Apache 2.0.
- **¿Cuánto tarda en frío?** ~55 s la primera llamada (cargar modelo en Metal), luego ~10-20 s.
- **¿Funciona en Windows?** Linux sí, Windows no probado.
- **¿Puede revisar varios archivos a la vez?** Sí, recursivo en directorios con `--recursive`. Paraleliza dos llamadas a la vez para no saturar la RAM.
- **¿Cuánto cuesta correr esto?** Cero. Una vez instalado, no hay llamadas a APIs externas.
- **¿Tiene falsos positivos?** ~6% medido en los fixtures del demo. Mucho menos que un revisor humano cansado.
- **¿Funcionaría para C++ o Rust?** El modelo entiende ambos; los analizadores estáticos no están conectados todavía.
