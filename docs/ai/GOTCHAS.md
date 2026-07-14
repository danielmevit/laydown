# Gotchas — traps that cost time

## Environment (WSL on /mnt/d)
- **CodeGraph does not auto-sync here** — run `codegraph sync` after editing code.
- **Git push needs Windows credentials:** `cmd.exe /c "git push origin dev"`.
- `core.filemode false` is set — don't "fix" phantom mode diffs.
- `git status` can take minutes: large untracked trees (`pressready-voice/venv`,
  `framer-demo/node_modules`, `dist/`, `build/`) on a slow /mnt mount. Prefer
  `git status -- <path>` or `git ls-files` when possible.
- **Showing the GUI needs Windows Python**, but it can be *constructed* headless in WSL:
  `QT_QPA_PLATFORM=offscreen python -m pressready --smoke` builds the real MainWindow and
  drives a load. The Windows-only calls (`ctypes.windll`, `os.startfile`) live in
  `run_gui()`/menu actions, not at import, so UI logic is testable from WSL.
- **Test venv (WSL):** `~/.venvs/pressready` (PyMuPDF + PyQt6 + pytest). D: has no room for
  it, so it lives on the WSL disk: `~/.venvs/pressready/bin/python -m pytest`.

## PyMuPDF facts worth not re-deriving
- **Box getters/setters use PyMuPDF's top-left origin**, the same space as `page.rect` —
  `page.trimbox = Rect(10, 50, …)` writes a y-flipped `/TrimBox` into the file. So
  `clip=page.trimbox` can be passed straight to `show_pdf_page` without converting.
- **`page.rect` is the CropBox, not the MediaBox** — they differ on trimmed PDFs.
- **Output is not byte-reproducible**: MuPDF randomises the trailer `/ID` per save. Page
  content streams *are* byte-identical, which is what `tests/test_determinism.py` asserts.
- **PDF has no in-place content transform** — scaling artwork means re-placing the page into
  a resized one with `show_pdf_page` (what `_scale` does), which returns a *new* document.

## Known code traps
- **Adding a field to the data model fails the build until you classify it** in
  `engine/capabilities.py` as HONOURED or NOT_IMPLEMENTED. That is deliberate: it is the
  guard against v2.0.0's defect, where the UI collected settings the engine ignored.
  If a setting isn't implemented yet, put it in NOT_IMPLEMENTED — the UI is then
  forbidden from offering it, and `tests/test_capabilities.py` enforces both directions.
- **`ui/schema.py` is the only place settings UI is declared.** Don't hand-build a
  control; add a schema entry. Its `target` is a dotted path into `Project`.
- **Display units are not a schema target** and never reach the engine. The model is
  millimetres throughout; `ValueStore.unit` + `LengthSpin` convert at the widget only.
- **`get_drawings()` ignores clipping**, and reports source paths at their *unclipped*
  extent transformed into sheet space. To check what actually reaches paper, render a
  pixmap and sample it (see `tests/test_source_boxes.py::TestBleed`).
- **`show_pdf_page(rotate=90)` turns anticlockwise** in sheet terms — a source's top edge
  ends up down the sheet's left. Verified against output, not assumed; bleed margins have
  to rotate with it (`geometry.place_page`).
- **`preprocessors.apply_preprocessors` may return a *different* document** (scaling has
  to rebuild pages). The caller owns the input; if the returned doc differs, close both.

## Build / packaging
- MSIX build needs a Windows 10 SDK; `certs/` (signing keys) is gitignored — first run of
  `build_msix.ps1` self-signs. Trust the cert once via elevated PowerShell (README).
- PyInstaller frozen mode resolves icons via `sys._MEIPASS` (`_app_icon()` in
  `ui/main_window.py`) — test icon changes in a frozen build, not just from source.

## Repo oddities
- `pressready-voice/` (tray dictation app) and `framer-demo/` (web demo) are **separate
  side-projects** living in this folder; both are excluded from CodeGraph via
  `codegraph.json`. `_legacy/` on disk is untracked leftover (already deleted from git).
