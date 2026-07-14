# TODO — prioritized (from the 2026-07-14 code review)

## P1 — correctness / trust
- [ ] **Close the UI ↔ engine gap.** Layout tab exposes features the engine silently
      ignores: booklet Mode (work-and-turn, work-and-tumble, perfect bound),
      right-to-left, move-fillers-to-middle, Signatures, Page Creep. Either implement
      them in `engine/impose.py` or hide/disable the controls until they exist.
      A print operator who sets creep and gets none finds out at the press.
      Same cleanup for `PreprocessorType` (12 declared, 3 implemented) and the
      tutorials HTML, which documents Signatures/Creep as working.
- [ ] **Engine test suite** (`tests/` is empty; engine is Qt-free and testable in WSL):
      - `booklet_page_order`: every source page appears exactly once; pair sums equal
        `padded-1`; blanks only when `n % 4 != 0`; total sides == padded/2 × 2.
      - `parse_page_range`: valid/invalid expressions, bounds, duplicates.
      - Geometry invariants: all cell rects inside sheet minus margins; no overlap.
      - Round-trip harness (recipe §5): generate a numbered PDF with PyMuPDF, impose it,
        reopen the output and assert page count, sheet size, and per-cell placement (via
        text extraction). This is the ground-truth loop for all future layout work.
- [ ] **Verify/fix the Scale preprocessor** — `_scale` only calls `set_mediabox`; it does
      not transform content (shrink factor crops, grow factor pads). Real scaling needs a
      content matrix. Write the round-trip test first, then fix.
- [ ] **Stop silent failures in `_reorder`** — bad expressions are ignored, and a partial
      list silently *drops* pages (`doc.select`). Raise `ValueError` like
      `parse_page_range` does, and surface it in the UI.

## P2 — robustness / maintainability
- [ ] Extract shared cell-geometry into the engine so `ui/preview_panel.compute_cells()`
      and `engine/impose.py` can't drift (WYSIWYG guarantee).
- [ ] `impose()`: close `src_doc` in a `try/finally`.
- [ ] Wire the export progress dialog's Cancel button to actually cancel the worker
      (currently it only hides); fix off-by-one "Sheet N+1 / N" label.
- [ ] Single-source the version string (currently in `pyproject.toml`, `__main__.py`,
      About dialog, `AppxManifest.xml`, `build_msix.ps1`, README).
- [ ] Headless `--smoke` mode (impose a bundled sample, exit 0/1) so the full stack is
      verifiable without eyes — then use it in the build script.

## P3 — repo organization
- [ ] Move `pressready-voice/` (unrelated dictation app) out to its own folder/repo.
- [ ] Decide `framer-demo/`'s home (own repo?) — its `node_modules` was untracked from
      git 2026-07-14 but the source remains here.
- [ ] Delete the on-disk `_legacy/` leftover (already removed from git history's tip).
