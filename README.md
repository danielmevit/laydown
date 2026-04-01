# PressReady v2

**PressReady** is a Windows desktop app for **PDF imposition** — laying out source pages on press sheets for commercial printing. Version 2 is written in **Python 3.10+** with **PyQt6** and **PyMuPDF (fitz)**. The earlier codebase lives in `_legacy/v1/`.

---

## Installers

| Format | File | Notes |
|--------|------|--------|
| **MSIX** | `PressReady_2.0.0.msix` | Standard install: Start Menu, Settings → Apps, uninstall from the system. |
| **Portable ZIP** | `PressReady_2.0.0-windows-x64.zip` | Run `PressReady.exe` after extract; no install. Handy for USB or locked-down machines. |

Built by `build_msix.ps1` into `installer_output/`.

---

## Interface

Work is grouped into four tabs:

| Tab | Role |
|-----|------|
| **Preprocessors** | Page transforms before imposition (rotate, scale, reorder; more types planned). |
| **Layout** | N-Up (e.g. 2/4-up), booklet (saddle-stitch), gutters, ranges — extended layouts on the roadmap. |
| **Sheet** | Output sheet size (A4, A3, Letter, Tabloid, custom), margins, orientation. |
| **Marks** | Crop, trim, registration, folding marks, labels, and related printer marks. |

---

## What works today (v2.0.0)

- Four-tab UI: Preprocessors, Layout, Sheet, Marks  
- Open PDF from a button or drag-and-drop  
- Preprocessors: rotate, scale, reorder  
- Layout: 2-up / 4-up, booklet (saddle-stitch, sheetwise), gutters, page range  
- Sheet: presets, per-side margins, orientation  
- Marks: crop, registration, trim, folding, text labels  
- Multi-sheet preview grid, zoom, and overlay options  
- PDF export in the background with a progress dialog  
- Vector imposition via PyMuPDF (`show_pdf_page` — page content not rasterized)  
- Menu bar (File, Edit, View, Help), recent files, in-app help (F1), dark theme with a consistent accent color  
- Custom app icon and MSIX-ready assets  

Details for this release: [CHANGELOG.md](CHANGELOG.md).

### Roadmap

- More preprocessors (e.g. duplicate/split pages, bleeds, crop/center, scripting)  
- More layout modes (work-and-turn/tumble, perfect binding, denser N-Up, signatures, creep, RTL)  
- More mark types (gap crop, perforation, color bars, barcode, plate names, custom marks)  
- Duplex and per-sheet rotation in the UI  
- Presets, undo/redo, full settings dialog, batch / hot folders  

---

## Repository layout

```
PressReady/
├── pressready/              # Application package
│   ├── __main__.py          # Entry point
│   ├── engine/              # Model, impose, marks, preprocessors
│   └── ui/                  # Main window and tabs
├── assets/icons/
├── tests/
├── _legacy/v1/
├── PressReady.spec
├── AppxManifest.xml
├── build_msix.ps1
├── pyproject.toml
├── CHANGELOG.md
├── installer_output/        # Build output (not in git)
└── README.md
```

---

## Run from source

```bash
cd PressReady
pip install PyQt6 PyMuPDF
python -m pressready
```

---

## Build MSIX (Windows)

Uses **PyInstaller** and the **Windows SDK** (`makeappx`, `signtool`).

**Requirements:** Python 3.10+ with PyQt6 and PyMuPDF, PyInstaller, and a Windows 10 SDK (example: `winget install Microsoft.WindowsSDK.10.0.26100`).

```powershell
powershell -ExecutionPolicy Bypass -File build_msix.ps1
```

This bundles the app, creates or reuses a cert under `certs/`, builds a signed `installer_output/PressReady_2.0.0.msix`, and a portable zip. Use `-SkipPyInstaller` if `dist/PressReady/` is already up to date.

**Trust the signing certificate once (elevated PowerShell):**

```powershell
Import-Certificate -FilePath "certs\PressReady.cer" -CertStoreLocation Cert:\LocalMachine\TrustedPeople
```

**Install / remove:**

```powershell
Add-AppxPackage -Path installer_output\PressReady_2.0.0.msix
Get-AppxPackage PressReadyTeam.PressReady | Remove-AppxPackage
```

Portable build: unzip `PressReady_2.0.0-windows-x64.zip` and run `PressReady.exe`.

---

## Design notes

1. **Engine vs UI** — The engine does not depend on Qt; a shared data model connects UI and logic.  
2. **Vectors** — Imposition uses `show_pdf_page` so quality follows the source PDF.  
3. **Preview** — Source pages render from the original file; sheet previews use a temporary imposed PDF; both use background threads.  
4. **Preprocessors** — They output a temporary PDF that feeds the imposition step.  
