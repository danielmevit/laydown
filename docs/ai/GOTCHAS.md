# Gotchas — traps that cost time

## Environment (WSL on /mnt/d)
- **CodeGraph does not auto-sync here** — run `codegraph sync` after editing code.
- **Git push needs Windows credentials:** `cmd.exe /c "git push origin dev"`.
- `core.filemode false` is set — don't "fix" phantom mode diffs.
- `git status` can take minutes: large untracked trees (`pressready-voice/venv`,
  `framer-demo/node_modules`, `dist/`, `build/`) on a slow /mnt mount. Prefer
  `git status -- <path>` or `git ls-files` when possible.
- **The GUI cannot run in WSL** — it uses `ctypes.windll` and `os.startfile`. Run the app
  with Windows Python. Engine code and its tests run fine in WSL (only needs PyMuPDF).

## Known code traps
- **The Layout tab lies:** booklet Mode (work-and-turn/tumble, perfect bound),
  right-to-left, move-fillers, Signatures, and Page Creep are all collected into
  `LayoutSettings` but the engine ignores them (only sheetwise saddle-stitch + N-Up are
  implemented). Don't treat the UI or `data_model.py` as the spec — `engine/impose.py`
  and `engine/preprocessors.py` are the truth. Same for `PreprocessorType`: 12 declared,
  3 implemented (rotate/scale/reorder).
- **Preview overlay geometry is duplicated** — `ui/preview_panel.compute_cells()`
  re-implements the cell math from `engine/impose.py`. Change one → change both, or the
  magenta overlays drift from the real output.
- **Scale preprocessor only resizes the mediabox** (`set_mediabox`) — it does not
  transform page content. Verify intended behavior before touching it (TODO.md).
- **Silent-failure style in preprocessors:** `_reorder` returns silently on a bad
  expression (and `doc.select` with a partial list *drops* unlisted pages).

## Build / packaging
- MSIX build needs a Windows 10 SDK; `certs/` (signing keys) is gitignored — first run of
  `build_msix.ps1` self-signs. Trust the cert once via elevated PowerShell (README).
- PyInstaller frozen mode resolves icons via `sys._MEIPASS` (`_app_icon()` in
  `ui/main_window.py`) — test icon changes in a frozen build, not just from source.

## Repo oddities
- `pressready-voice/` (tray dictation app) and `framer-demo/` (web demo) are **separate
  side-projects** living in this folder; both are excluded from CodeGraph via
  `codegraph.json`. `_legacy/` on disk is untracked leftover (already deleted from git).
