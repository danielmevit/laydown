# Changelog

All notable changes to PressReady are documented here.

---

## [Unreleased]

### Phase 1 — Ground truth (2026-07-14)

**Tests** — `tests/` went from empty to 96 tests. The centrepiece is a round-trip bench harness
(`tests/helpers.py`): build a source PDF carrying findable tokens, impose it, read the tokens back
out of the *output*, and assert every page landed where the geometry says. Cell maths is re-derived
in the tests rather than imported, so they can disagree with the engine. Also invariants for
saddle-stitch ordering, page-range parsing, margin containment, determinism, and culture-invariance.

**Fixed** (each was reproduced by a failing test first):
- `impose()` leaked the source document whenever imposition raised; output documents leaked on a
  failed save. Both now close in `finally`.
- **Reorder silently deleted pages.** `"4,3"` on a four-page document meant "keep two" — a reorder
  is not a delete. A partial, out-of-range or unparseable order now raises with a message that says
  what to type instead. Bad expressions used to be ignored entirely.
- **Scale Pages cropped instead of scaling.** It only moved the MediaBox, so reducing a page cut its
  bottom-right away rather than shrinking the artwork. It now re-places page content vectorially and
  carries trim/bleed/art boxes with it.
- Booklet marks counted **sides as sheets** — a 4-side (2-sheet) booklet labelled itself "Sheet 1 of
  4", and collating marks stepped per side, so a collated stack showed the wrong staircase.
- Removed a dead expression in `impose.py` whose branches were identical.

**Added**
- `python -m pressready --smoke` — headless end-to-end self-check (build a sample, impose it, verify
  the output, construct the real window offscreen, exit 0/1). Runs in WSL and in a frozen build.
- Proper CLI entry point (`--version`, optional PDF argument).
- Version single-sourced from `pressready/__init__.py`; `pyproject.toml` reads it dynamically and
  the About dialog no longer hardcodes it.

### Planning (2026-07-14)

- **Reference study** — `docs/ai/REFERENCE_STUDY.md`: Imposition Wizard 3 (installed build:
  feature and domain model; its tab list is where PressReady's four tabs and unimplemented enums
  came from) and Toolcraft (`@pixel-point/toolcraft`: schema-driven control panel, layout laws,
  dark token system). No code from either was copied.
- **`ROADMAP.md`** — six phases from a full code review: ground-truth bench harness → box-aware
  imposition → schema-driven panel with an engine capability contract → Toolcraft-style UI →
  the promised layout depth → marks/units/preflight. Absorbs the earlier `TODO.md`, which is
  removed so there is one work list.
- **DECISIONS** — keep PyQt6/PyMuPDF and port Toolcraft's design language rather than its stack;
  a control the engine doesn't honour must not exist in the UI; IW is a domain reference, not a
  feature target; brand accent stays orange.

### Project organization (2026-07-14)

- Adopted the AI-project standard (`_refs/ai-project-setup-playbook.md`): added `AGENTS.md`
  router and `docs/ai/` (START_HERE, DECISIONS, GOTCHAS, DESIGN_SYSTEM).
- **CodeGraph**: indexed the repo (`.codegraph/` gitignored, per-machine); `codegraph.json`
  excludes `_legacy/`, `framer-demo/`, `pressready-voice/`.
- **Git model**: work now happens on `dev`; `main` is releases only.
- **Hygiene**: untracked `framer-demo/node_modules` (2,196 files were committed); added
  `node_modules/` and `.codegraph/` to `.gitignore`; set `core.filemode false` for WSL.

### Licensing

- Project relicensed under **GNU Affero General Public License v3.0 only (AGPL-3.0-only)**. Added `LICENSE`, `LICENSING.md`, and `NOTICE`; updated `README.md` and `pyproject.toml`.

---

## [2.0.0] — 2026-02-19

### Installers

- **MSIX installer** — Native Windows packaging via `build_msix.ps1`. Produces `PressReady_2.0.0.msix` in `installer_output/`. Double-click to install; integrates with Start Menu, Settings → Apps, and Add/Remove Programs.
- **Portable ZIP** — Produced alongside MSIX as `PressReady_2.0.0-windows-x64.zip`. Extract and run `PressReady.exe` with no installation. Suitable for USB drives, portable use, or restricted environments.
- Removed Inno Setup and any third-party installer dependencies. MSIX uses only the free Windows 10 SDK (`makeappx.exe`, `signtool.exe`).

### Build Pipeline

- **PyInstaller** — One-dir bundle with `PressReady.spec`. Includes PyQt6, PyMuPDF, and app icons.
- **build_msix.ps1** — Single script to build both MSIX and portable ZIP. Auto-creates self-signed certificate on first run.
- **AppxManifest.xml** — MSIX manifest with app identity, icons, and runFullTrust capability.
- **assets/icons/msix/** — MSIX tile icons (Square44, Square150, StoreLogo).

### Code

- **pressready/ui/main_window.py** — `_app_icon()` now handles PyInstaller frozen mode via `sys._MEIPASS` for correct icon resolution in bundled builds.

### Project Structure

- Added: `AppxManifest.xml`, `build_msix.ps1`, `CHANGELOG.md`, `assets/icons/msix/`
- Build output: `installer_output/` (MSIX + ZIP), `dist/`, `build/`, `msix_stage/` (gitignored)
- Signing certs: `certs/` (gitignored)

---

## [1.x] — Archived

Original v1 code is in `_legacy/v1/`. See README for v2 feature list.
