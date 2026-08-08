# Yoink — common dev commands
#
# Windows (PowerShell):  make run
# macOS / Linux:         make run
#
# Requires GNU Make. On Windows, install via `choco install make` or use Git Bash.

.PHONY: help venv install run run-minimized test lint lint-fix build build-exe compose-html clean

ROOT := $(CURDIR)

ifeq ($(OS),Windows_NT)
  PYTHON      := $(ROOT)/.venv/Scripts/python.exe
  PIP         := $(ROOT)/.venv/Scripts/pip.exe
  PY          := python
  PATHSEP     := ;
else
  PYTHON      := $(ROOT)/.venv/bin/python
  PIP         := $(ROOT)/.venv/bin/pip
  PY          := python3
  PATHSEP     := :
endif

export PYTHONPATH := $(ROOT)$(PATHSEP)$(ROOT)/src

help:
	@echo Yoink — available targets:
	@echo   make venv          Create .venv
	@echo   make install       pip install runtime + dev requirements
	@echo   make run           Start the desktop app
	@echo   make run-minimized Start hidden to tray (--minimized)
	@echo   make test          Run pytest
	@echo   make lint          Run ruff (same check as CI)
	@echo   make lint-fix      Run ruff with --fix
	@echo   make compose-html  Re-assemble src/web/index.html from partials
	@echo   make build         PyInstaller exe + Inno Setup installer (Windows)
	@echo   make build-exe     PyInstaller exe only
	@echo   make clean         Remove build/dist artifacts

venv:
	$(PY) -m venv .venv

install: venv
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt

run: compose-html
	$(PYTHON) src/main.py

run-minimized: compose-html
	$(PYTHON) src/main.py --minimized

compose-html:
	$(PYTHON) build.py --compose-html

test:
	$(PYTHON) -m pytest tests/ -q

lint:
	$(PYTHON) -m ruff check .

lint-fix:
	$(PYTHON) -m ruff check . --fix

build:
	$(PYTHON) build.py

build-exe:
	$(PYTHON) build.py --exe-only

clean:
	$(PYTHON) -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ('build','dist')]; [pathlib.Path(f).unlink(missing_ok=True) for f in ('Yoink.spec',)]"
