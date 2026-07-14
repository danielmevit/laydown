# START HERE — PressReady

## What this is
PressReady v2 — a Windows desktop app for **PDF imposition** (laying out source pages on
press sheets for commercial printing). Python 3.10+, PyQt6 UI, PyMuPDF (fitz) engine.
v2.0.0 shipped 2026-02-19 (MSIX + portable ZIP). License: AGPL-3.0-only.

## Current priority
Work through **TODO.md**, top to bottom. The two big items:
1. **Close the UI ↔ engine gap** — the Layout tab exposes booklet modes, right-to-left,
   fillers, signatures, and page creep that the engine silently ignores. For a prepress
   tool, silently wrong output is the worst failure mode.
2. **Engine test suite** — `tests/` is empty. The engine is Qt-free and fully testable
   headless (see TODO.md for the invariant list).

## How to run
- **App (Windows Python, not WSL):** `pip install PyQt6 PyMuPDF` then `python -m pressready`
- **Engine tests (WSL or Windows):** `pip install -e .[dev]` then `pytest`
- **Installer build (Windows PowerShell):** `powershell -ExecutionPolicy Bypass -File build_msix.ps1`

## Layout of the work
- `pressready/engine/` — data model, imposition, marks, preprocessors. **No Qt imports.**
- `pressready/ui/` — main window, four settings tabs, preview canvas.
- Everything else structural: ask CodeGraph (`codegraph explore "..."`), don't crawl.

## Links
- Recent work → `CHANGELOG.md` · Task queue → `TODO.md`
- Why it's built this way → `docs/ai/DECISIONS.md`
- Traps → `docs/ai/GOTCHAS.md` · Theme/styling → `docs/ai/DESIGN_SYSTEM.md`
