# START HERE — PressReady

## What this is
PressReady — a desktop app for **PDF imposition** (laying out source pages on press sheets
for commercial printing). Python 3.10+, PyQt6 UI, PyMuPDF (fitz) engine. Runs on Windows,
macOS and Linux. Current version **0.3.0**. License: AGPL-3.0-only.

## Current priority
**v0.3.0 is built and pushed on `dev`; see `ROADMAP.md` backlog for what's next.** All six
planned phases have landed (CHANGELOG.md has the detail). The plan was grounded in a study of
Imposition Wizard 3 and Toolcraft — `docs/ai/REFERENCE_STUDY.md`.

Two things to know before changing anything:
- **The UI cannot offer a setting the engine ignores.** `engine/capabilities.py` classifies
  every setting and the tests fail if one escapes. That is the guard against 0.2.0's central
  defect; don't route around it.
- **Settings UI is declared, not written.** Add a schema entry in `ui/schema.py`; don't
  hand-build controls.

Releasing: tag `vX.Y.Z` and `.github/workflows/release.yml` builds all five artifacts. The
website deploys from `main`.

## How to run
- **App:** `pip install -e .` then `python -m pressready`
- **Tests:** `pip install -e ".[dev]"` then `pytest` — 243 of them, no display needed.
  In WSL use the venv at `~/.venvs/pressready` (see GOTCHAS).
- **Self-check:** `python -m pressready --smoke` — headless, end to end, exits 0/1.
- **Packaging:** `packaging/{windows,linux,macos}/` — each runs on its own OS.

## Layout of the work
- `pressready/engine/` — data model, geometry, imposition, marks, preprocessors,
  preflight, capabilities. **No Qt imports** — that's what makes it testable.
- `pressready/ui/` — `schema.py` (what the panel offers), `panel.py` (renders it),
  `components.py`, `theme.py` (every colour), preview canvas.
- `site/` — the Astro website. `packaging/` — the installers.
- Everything else structural: ask CodeGraph (`codegraph explore "..."`), don't crawl.

## Links
- The plan → `ROADMAP.md` · Recent work → `CHANGELOG.md`
- Why it's built this way → `docs/ai/DECISIONS.md`
- What the references taught us → `docs/ai/REFERENCE_STUDY.md`
- Traps → `docs/ai/GOTCHAS.md` · Theme/styling → `docs/ai/DESIGN_SYSTEM.md`
