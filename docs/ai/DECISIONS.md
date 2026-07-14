# Decisions — durable "why" choices

- **Python + PyQt6 + PyMuPDF for v2** (over the v1 codebase). v1 is archived; the repo's
  history has it under `_legacy/v1` (later removed from git; a copy may linger on disk).
- **Vector imposition via `show_pdf_page`** — pages are embedded as XObjects, never
  rasterized, so output quality always equals source quality. This is the core product
  promise; nothing in the pipeline may rasterize page content.
- **Engine/UI split with a shared dataclass model** (`pressready/engine/data_model.py`).
  The engine imports no Qt. UI tabs each expose a `get_*()` that assembles the `Project`.
  Rationale: headless testability + the engine could later back a CLI/batch mode.
- **Preview = render the real imposed PDF** — the preview canvas imposes to a temp PDF and
  rasterizes that, so the preview is the actual output, not a simulation. (Caveat: overlay
  cell geometry is computed separately — see GOTCHAS.)
- **MSIX + portable ZIP, no third-party installer** — packaging uses only the free Windows
  10 SDK (`makeappx`, `signtool`) via `build_msix.ps1`. Inno Setup was removed.
- **AGPL-3.0-only** license (relicensed after 2.0.0; see LICENSING.md).
- **mm in the model, points in the engine** — all user-facing/model dimensions are mm;
  conversion to PDF points happens at the engine boundary (`utils.mm_to_pt`).
