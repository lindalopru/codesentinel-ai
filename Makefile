.PHONY: setup demo cli web test lint clean doctor docker help install

SHELL  := /bin/bash
PYTHON ?= .venv/bin/python
PIP    ?= .venv/bin/pip

# Default target shows help
.DEFAULT_GOAL := help

help: ## Show this help
	@echo "CodeSentinel AI — Make targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk -F': .*?## ' '{printf "  %-12s %s\n", $$1, $$2}'

.venv:
	python3.12 -m venv .venv
	$(PIP) install --upgrade pip wheel
	$(PIP) install -r requirements.txt
	$(PIP) install -e .

install: .venv ## Create venv and install package in editable mode

setup: ## Full setup (Ollama + model pull + venv + deps)
	bash setup.sh

doctor: .venv ## Verify environment is healthy
	$(PYTHON) -m codesentinel.utils.doctor

demo: .venv ## Run sample reviews on bundled buggy examples
	$(PYTHON) -m cli.main review examples/buggy_python.py
	$(PYTHON) -m cli.main review examples/insecure_js.js
	$(PYTHON) -m cli.main review examples/messy_typescript.ts
	$(PYTHON) -m cli.main review examples/legacy_java.java

cli: .venv ## Show CLI help
	$(PYTHON) -m cli.main --help

web: .venv ## Launch Gradio web UI at http://127.0.0.1:7860
	$(PYTHON) -m web.app

test: .venv ## Run pytest with coverage
	$(PYTHON) -m pytest --cov=codesentinel --cov-report=term-missing

lint: .venv ## Run ruff + black --check + mypy
	$(PYTHON) -m ruff check .
	$(PYTHON) -m black --check .
	-$(PYTHON) -m mypy codesentinel

format: .venv ## Auto-format with black + ruff --fix
	$(PYTHON) -m black .
	$(PYTHON) -m ruff check --fix .

clean: ## Remove venv and caches
	rm -rf .venv .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete

docker: ## Build docker images (web + ollama-bridge)
	docker compose build
