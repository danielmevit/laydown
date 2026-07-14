# Changelog

All notable changes to PressReady are documented here.

---

## [Unreleased]

### Project organization (2026-07-14)

- Adopted the AI-project standard (`_refs/ai-project-setup-playbook.md`): added `AGENTS.md`
  router and `docs/ai/` (START_HERE, DECISIONS, GOTCHAS, DESIGN_SYSTEM), plus `TODO.md`
  with prioritized findings from a full code review.
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
