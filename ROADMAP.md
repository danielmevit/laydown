# Roadmap — PressReady

The plan. Grounded in `docs/ai/REFERENCE_STUDY.md` (Imposition Wizard 3 + Toolcraft) and a full
read of the code on 2026-07-14. Phases are ordered so each one is verifiable before the next
starts (`_refs/ai-full-build-recipe.md` §4). Sizes: **S** ≈ a session, **M** ≈ a few, **L** ≈ a phase of its own.

## Done
- **0.2.0** (2026-02-19) — four-tab UI, N-Up 2/4, saddle-stitch booklet, 6 mark types,
  vector imposition, multi-sheet preview, MSIX + portable ZIP.
- **2026-07-14** — AGPL relicense; AI-project standard adopted (AGENTS.md, docs/ai/,
  CodeGraph, `dev` branch); `framer-demo/node_modules` untracked.
- **2026-07-14/15 — Phases 1–6 all landed.** See CHANGELOG.md. In short: a ground-truth
  bench harness and 230 tests where there were none; box-aware imposition (v2 imposed the
  MediaBox, so press-ready PDFs were placed wrong and marked wrong); a capability contract
  that fails the build if the UI offers a setting the engine ignores; a schema-driven,
  Toolcraft-styled panel with undo, presets and per-section reset; arbitrary N-Up grids,
  auto-rotate, signatures, perfect binding, creep and RTL; units, four new mark types and
  preflight. Engine order was 1 → 2 → 5 → 6 → 3 → 4: with everything shipping together the
  old UI never reached anyone, so the schema was written once against a finished engine.

## Not done from the original plan (deliberately)
- **Work-and-turn / work-and-tumble.** Not orderings but press-form techniques: both forms
  go on one double-size plate and the sheet is printed twice from it. Subtly wrong here
  wastes plates and paper, and the semantics can't be validated without a pressman. Removed
  from the model rather than left as controls that do nothing — which is the exact defect
  this whole series exists to remove. Backlog, below.

---

## The one-paragraph version (as diagnosed 2026-07-14, now addressed)

PressReady's engine was small, clean, and genuinely vector-true. Its problem was never code
quality — it was that **nothing verified the output and the UI promised things the engine
didn't do**. The Layout tab collected booklet modes, right-to-left, fillers, signatures and
page creep that `impose.py` silently dropped on the floor; 9 of 12 preprocessors didn't
exist; and every placement used the source MediaBox, so a real press-ready PDF (which carries
a TrimBox and bleed) imaged the wrong area. For a prepress tool, silently-wrong output is the
worst possible failure, and it was the *easiest* thing to produce. All six phases below have
landed; the guard that keeps it fixed is `engine/capabilities.py` plus its tests, which fail
the build if a setting is added that the engine doesn't read.

---

## Phase 1 — Ground truth · **M** · no user-visible change
Everything after this changes imposition output. Without a harness we'd be guessing, and
`tests/` is empty today. This is recipe §5's evaluation-first loop, applied to imposition.

- **Bench harness.** `make_source_pdf(n, w_mm, h_mm, trim_mm=…)` builds a synthetic source whose
  every page carries its number plus corner markers at known coordinates. Impose it, reopen the
  output, and assert via `page.get_text("words")` coordinates that **source page N landed inside
  the expected cell rect on the expected sheet**, right way up, aspect preserved. That turns "the
  preview looks right" into a number. On failure, dump the rendered sheet + expected-cell overlay
  as a PNG — recipe §5 is explicit that the agent must *look at the pictures*, not just the diff.
- **Invariants, not snapshots** (recipe §6): `booklet_page_order` — every page exactly once, pair
  sums == `padded-1`, blanks only when `n % 4 != 0`; `parse_page_range` — bounds and bad input;
  geometry — cells inside sheet-minus-margins, no overlap, gutters honoured; determinism — same
  input, byte-identical output; **culture-invariance — run one test under `de_DE`** (comma decimals
  silently corrupt PDF number syntax).
- **`python -m pressready --smoke`** — impose a bundled sample headless, exit 0/1, so the full
  stack is verifiable without eyes and the build script can gate on it (recipe §4).
- **Fix under cover of the new tests:** `impose()` leaks `src_doc` on any exception (`try/finally`);
  `_reorder` swallows bad expressions *and* silently drops pages not in a partial list (`doc.select`)
  → raise `ValueError` like `parse_page_range` does; `_scale` only calls `set_mediabox`, so it crops
  or pads rather than scaling — decide real content scaling vs. renaming it "Resize Canvas";
  booklet's "Sheet N of M" counts **sides**, not sheets, and collating marks step per side;
  the `preset_label` line in `impose.py` is a dead expression (both branches return the same value).

**Verify:** `pytest` green in WSL; `--smoke` exits 0.

## Phase 2 — Box-aware imposition · **M** · correctness for real press PDFs
`show_pdf_page` is called without `clip`, so **every placement uses the source MediaBox**. Press-ready
PDFs carry TrimBox/BleedBox — exactly PressReady's target user — and for those the tool currently
images the wrong area and puts crop marks in the wrong place. IW has had box handling since forever
(`bleedBoxSize`, `Bleeds Override`); this is table stakes, not a feature.

- Source-box selection (Media/Crop/Trim/Bleed) in the model; pass `clip=` through to `show_pdf_page`.
- Bleed: place the trim box, pull bleed from the bleed box, anchor crop/trim marks to the trim rect.
- Warn when a source has no TrimBox or the boxes disagree (feeds the Phase 6 preflight).

**Verify:** a bench fixture with a known trim+bleed asserts the trim rect lands exactly on the cell.

## Phase 3 — One truth for the settings panel · **L** · no visual change yet
Toolcraft's structural idea, recreated in PyQt6. This is the phase that kills the lie permanently.

- **`ui/schema.py`** — the panel declared, not wired: sections (titled for the entity they edit) →
  controls with `type`, `target`, `default`, `label`, `description`, `visible_when`.
- **`ui/panel.py`** — renders a schema to widgets and owns get/set/reset. Replaces four hand-wired
  tabs and four near-identical `get_settings()` methods.
- **`engine/capabilities.py`** — the engine declares which model fields it actually honours, and a
  **test asserts every schema target is engine-backed**. After this, a control that does nothing
  fails CI. That's the whole point.
- Unimplemented branches **leave the schema** rather than being disabled (Toolcraft's law:
  `visibleWhen`, never `disabled`) — booklet modes, RTL, fillers, signatures and creep disappear
  from the UI until Phase 5 actually lands them.
- **Generate the tutorials HTML from the schema** so the help can't drift from the app again (it
  currently documents Signatures and Page Creep as working features).
- Nearly free once values live in one store, and each deletes a stub that currently lies:
  per-section reset · **presets** (serialise values — the Settings dialog's "future update"
  placeholder) · **undo/redo** (value snapshots — the greyed-out Edit menu).

**Verify:** parity test — for a matrix of settings the schema panel produces the same `Project` as
the old tabs; capability test green; Phase 1 bench unchanged.

## Phase 4 — The Toolcraft-style UI · **M** · visual only, no logic change
Same edit surface as Phase 3, deliberately split so each half is verifiable: schema behind the old
look first, then the new look over proven logic.

- **`ui/theme.py`** — tokens in one place: neutral ramp, radii 2/4/6/8/12, spacing and type scale,
  4px scrollbars with 999px thumbs and ~44px minimum. Qt has no `oklch()`/`color-mix()`, so the
  palette is computed to hex in Python and emitted into QSS.
- **Component kit:** 36px collapsible section headers with per-section reset · full-width sliders
  and segmented controls (≤4 options, ≤9 chars) · 50/50 rows only for short related pairs · switches
  labelled for the thing, not `Enable X` · keyboard-only focus rings · no animation while mounting.
- **Generate PDF moves to a sticky footer** (Toolcraft puts final delivery actions in `panelActions`,
  never the toolbar or canvas).
- **Recommendation: keep the orange `#D07B24` accent** — it's the brand and it's baked into the app
  and MSIX icons — and adopt Toolcraft's neutrals, density and control anatomy. That reads as
  "similar to Toolcraft" without borrowing its identity. Flipping to their blue `#0c8ce9` is one
  constant if you'd rather have the literal look.
- **Preview quality (visible today):** sheets render at 72 DPI and are then upscaled by the zoom
  factor, so "Actual size" on a 96-DPI screen is a 1.33× blow-up of a 72-DPI raster — it looks soft.
  Render at zoom/DPI-aware resolution, cache, re-render debounced.
- **Preview scale:** every settings change re-imposes the *entire document* to a temp PDF and
  re-renders *every* sheet. On a 200-page job that's brutal. Cull to the viewport and reuse the
  imposed document. (Toolcraft models this explicitly as `performanceRole: workload | responsiveness`.)

**Verify:** `--smoke` + a manual pass on Windows; before/after screenshots in the CHANGELOG.

## Phase 5 — The layout depth the UI already promised · **L**
Each item lands with a bench test, and only then does its schema control come back.
- Real booklet modes: work-and-turn, work-and-tumble, perfect bound; right-to-left; fillers to the
  middle; signatures; creep (shift in/out/both and scale — IW models this as a creep *calculator*).
- **Generalise N-Up** to arbitrary rows × columns with auto-fit and auto-rotate. Today it's
  hardcoded to 2×1 and 2×2; IW has plain `Rows`/`Columns`. This is a small engine change for a
  large feature gain.

## Phase 6 — Marks, units, preflight · **M**
- **Units: mm / cm / in / pt.** IW ships all four; PressReady is mm-only, which is awkward for the
  Letter/Tabloid users it already has presets for. Cheap — the model is already mm-internally.
- **Marks:** gap crop, perforation, angle, colour bar, and **custom-mark PDFs** — IW's `Placeholders/`
  folder reveals custom marks are just user PDFs stamped by rule, which the existing `show_pdf_page`
  path already does. Highest value per line of code on this list.
- **Preflight panel** (IW's `PreflightDashboard`): pages don't divide evenly, margins too large,
  no TrimBox, source box mismatch. The engine already throws "Margins/gutters too large for sheet
  size" *at export time* — preflight is surfacing that live instead of at the press.

---

## Backlog
- **Step & Repeat** and **Cut Stack** — of IW's six layout modes these two carry real label/card
  work; Dutch Cut is niche and Shuffle is deprecated even in IW.
- **CLI / batch / hot folders** — the engine is already Qt-free for exactly this (`DECISIONS.md`),
  and IW validates the shape: one engine behind a GUI, a console binary, and a plugin.
- Barcode marks — one or two symbologies (Code128, DataMatrix), not IW's thirty.
- Repo hygiene: single-source the version (it's in six places today) · extract `pressready-voice/`
  (an unrelated tray dictation app living in this repo, and the main reason `git status` takes
  minutes) · decide `framer-demo/`'s home · delete the untracked `_legacy/` leftover.

## Not doing (and why)
- **Rewriting as a Toolcraft web app.** Toolcraft is React/Vite; PressReady is a shipped desktop
  tool whose value *is* the PyMuPDF vector engine and MSIX packaging. Port the design language,
  keep the stack. (Recorded in `docs/ai/DECISIONS.md`.)
- **Cloning IW's feature list.** It's the source of the promises the UI can't keep. Take its domain
  model and its one-engine-many-front-ends architecture; leave Shuffle, the barcode zoo, the
  licensing machinery, and the Acrobat plugin.
