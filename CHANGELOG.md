# Changelog

All notable changes to Laydown (formerly PressReady) are documented here.

---

## [0.4.3] — 2026-07-18

- **Security: the dropdown-chevron image is written to the per-user cache, not the shared
  temp dir.** 0.4.2 wrote it to a predictable path in the world-writable temp directory, which
  on a multi-user system invites a symlink/collision (the save would follow a planted symlink).
  Low risk for a single-user desktop app, but real; it now goes to `QStandardPaths`
  `CacheLocation` with a private `mkdtemp` (0700) fallback. Flagged by the commit security review.

## [0.4.2] — 2026-07-18

UI fixes and polish from hands-on use.

- **Fixed: zoom no longer spawns windows.** Clicking zoom in/out opened stray windows of the
  sheets and dislocated the preview. `_clear_grid` called `setParent(None)` on each sheet
  widget, which reparents a *visible* child to the desktop — turning it into a top-level
  window — and every zoom rebuilds the grid. Now `hide()` + `deleteLater()`. Reproduced in
  isolation and pinned by `tests/test_preview_zoom.py`.
- **Double-click the empty canvas to open a PDF**, alongside Ctrl+O and drag-and-drop.
- **Page numbers in the preview are bigger and regular weight** (were smaller and bold).
- **Distinct fit-page and actual-size icons.** They were both a square-with-corners and easy
  to confuse; actual-size is now a plain sheet rectangle.
- **The four settings tabs (Source/Layout/Sheet/Marks) are centred** in the panel header
  instead of clustering left.
- **The zoom/fit group is right-aligned** in the toolbar; the column-view buttons stay left.
- **Dropdowns show a chevron.** Styling the combo boxes had suppressed Fusion's native arrow,
  so they lost their "this opens a list" cue; a Lucide chevron is rendered back in.

## [0.4.1] — 2026-07-17

- **UI icons are now the [Lucide](https://lucide.dev) set.** The toolbar (column views, zoom,
  fit-to-width / fit-page / actual-size), the four settings-tab glyphs (source, layout, sheet →
  ruler, marks → crop) and the Generate button were hand-drawn with QPainter; they're now the
  verbatim Lucide SVGs, rendered through QtSvg and tinted to the theme. Consistent stroke weight,
  crisp at any DPI. Lucide is ISC-licensed; attribution is in `NOTICE`.
- `laydown/ui/icons.py` holds the icon set with a test that guards every name, so a mistyped glyph
  fails CI instead of crashing the window. QtSvg is bundled automatically by the existing
  PyInstaller collection (verified in a frozen Linux build).

## [0.4.0] — 2026-07-16

**PressReady is now Laydown.** Fujifilm ships "Revoria XMF PressReady" — a prepress workflow
product in this exact field — so the old name was a collision waiting to matter. "Laydown" is
what printers call the imposition arrangement itself. Same app, same code lineage.

- **Windows sees a different app.** The package identity changed (`PressReadyTeam.PressReady`
  → `LaydownTeam.Laydown`), so an existing PressReady install does not upgrade — remove it once:
  `Get-AppxPackage PressReadyTeam.PressReady | Remove-AppxPackage`.
- New signing certificate (its subject must match the new publisher), executable/artifact names
  (`Laydown.exe`, `Laydown-<version>-<platform>`), settings under `HKCU\Software\Laydown`, repo
  at `github.com/danielmevit/laydown`, site at <https://danielmevit.github.io/laydown/>.
- Releases 0.2.0 and 0.3.0 keep their PressReady-named files — history is not rewritten.

### MSIX signing fixed (0x800B010A)

The 0.3.0 release pipeline signed each MSIX with a certificate minted on the CI runner and
destroyed with it, so the public certificate users needed to trust never existed anywhere they
could get it — every install failed with 0x800B010A. Releases are now signed with one stable
certificate (kept in repo secrets, valid to 2031); its public half ships as
`Laydown-msix-signing.cer` beside the installer, and the notes carry the one-time trust command.
The 0.3.0 Windows assets were rebuilt and replaced in place.

## [0.3.0] — 2026-07-15

Version restarted at **0.3.0** to match how the rest of these projects are numbered. The
February release was renumbered from v2.0.0 to **v0.2.0** to suit — same commit, same binaries,
new label.

Those binaries still declare `2.0.0.0` inside the MSIX, which renaming a tag can't change, and
MSIX refuses to install an older version over a newer one. So if you have February's build
installed, remove it before putting 0.3.0 on:
`Get-AppxPackage PressReadyTeam.PressReady | Remove-AppxPackage`.

### Packaging — Windows, macOS, Linux

- **Four artifacts, built by CI on every version tag** (`.github/workflows/release.yml`):
  Windows x64 (MSIX + portable ZIP), macOS **arm64 and Intel** (.dmg), and Linux x86_64
  (portable tar.gz). PyInstaller can't cross-compile, so each runs on its own runner. Every job
  runs the tests *and* `--smoke` before packaging, and the Linux job smoke-tests the built
  bundle itself.
- **No 32-bit Windows build.** It was planned and attempted, and it can't be done: PyQt6 ships
  no `win32` wheel (only `win_amd64`/`win_arm64`), so pip falls back to the source tarball and
  tries to build Qt with qmake. A 32-bit build would mean compiling Qt from source for x86.
  The claim has been removed from the README and the site rather than left standing.
- One cross-platform `PressReady.spec` (per-OS icon, macOS `.app` bundle, PDF file
  association); `packaging/{windows,linux,macos}/` scripts replace `build_msix.ps1`.
- Trimmed unused Qt modules (WebEngine, Quick, QML, Multimedia, …) out of the bundle.
- **Windows build fix:** `build.ps1` failed to parse before running a line. Windows PowerShell
  5.1 reads a BOM-less `.ps1` as ANSI (cp1252), so a UTF-8 em-dash in a `Write-Host` message
  arrived as three bytes ending in a curly quote — which PowerShell treats as a string
  terminator, unbalancing every brace after it. The script is now pure ASCII, and
  `tests/test_packaging.py` enforces that from Linux.
- **Linux build fix:** the launcher script was named `pressready` next to the `PressReady`
  binary. On a case-insensitive filesystem — i.e. building from WSL against a Windows drive —
  those are the same file, so the script overwrote the 100 MB binary and then exec'd itself
  forever. CI would never have caught it (ext4 is case-sensitive). The launcher is gone, and
  the build now fails loudly if the binary comes out suspiciously small.

### The website

- `site/` — an Astro page published to <https://danielmevit.github.io/pressready> by
  `.github/workflows/deploy.yml`. **That workflow was replaced**: it uploaded the repository
  root, which would have served the raw repo instead of a site.

### Fixed

- **The settings panel painted itself near-white.** `QScrollArea`'s viewport is a child widget,
  so a `QScrollArea { background: transparent }` rule never reached it and it fell back to the
  platform's light palette — putting near-white section titles on a near-white background,
  unreadable. Fixed with a real dark `QPalette` plus viewport rules, so nothing depends on a
  stylesheet reaching every widget.
- **Undo, redo and preset loads only updated length fields.** Every other control — segmented,
  select, switch, text — kept showing its old value while the store, the preview and the
  exported PDF had the new one. All controls now follow the store, with a test that no control
  can be added without being resyncable.
- The mark editor's settings panel showed empty at startup and hid itself after choosing
  artwork (a stray line absorbed into the wrong method).
- Colours and fonts are read from `ui/theme.py` everywhere; the preview panel and the two
  collection editors had hardcoded leftovers.
- Bounded the preprocessor/mark lists and gave them empty states instead of a tall black box.

### Docs

- README rewritten in plain language — what it does, who it's for, what it can't do yet.

### Phase 6 — Marks, units, preflight (2026-07-15)

- **Units** — mm / cm / in / pt (View → Units). The model stays millimetres throughout; the
  unit is display-only, so a shop doing Letter work can type inches and nothing downstream
  has to care.
- **New marks** — gap crop marks (cuts that run to the sheet edge, for ganged work),
  perforation marks, a process + grey-ramp colour bar, and **custom marks: any PDF, stamped
  on the sheet**. That last one came straight out of the reference study — Imposition
  Wizard's `Placeholders/` folder holds `missing-bull-eye.pdf` and friends, which gives away
  that a custom mark is just artwork placed by rule. `show_pdf_page` already did that, so a
  shop can drop in its own bull's-eye or house colour bar. A missing or corrupt mark PDF
  never takes the job down.
- **Preflight** — problems surface while there's still time to fix them, instead of arriving
  as an exception after Generate (or at the guillotine): impossible margins, no trim box,
  bleed with no artwork behind it, mixed page sizes, page counts that don't fold, pages
  being scaled. Graded deliberately: A4 two-up on A3 lands near 97% and that is the job this
  tool is *for*, so slight scaling is a note and only a real reduction raises the strip.
  Notes stay in Help → Preflight (F7) rather than sitting on screen training people to
  ignore it.

### Phase 4 — The Toolcraft-style UI (2026-07-15)

- **`ui/theme.py`** — every colour, radius and size in one place, plus the whole stylesheet.
  Neutrals are authored in **OKLCH** and converted to hex at import (Qt has no `oklch()` or
  `color-mix()`). The converter is exact: `oklch(0.269)` → `#262626`, matching Toolcraft's
  own literal for the same token.
- **`ui/components.py`** — the control kit: a real switch instead of a checkbox, a
  full-width segmented control, 36px collapsible section headers with a per-section reset,
  label-above field rows, hairline 4px scrollbars.
- **Generate PDF moved to a sticky footer** — Toolcraft pins final delivery actions rather
  than burying them in a toolbar.
- **The accent stays orange.** It's the product's identity and is already in the app icon and
  MSIX tiles; what's borrowed from Toolcraft is the structure, density and control anatomy.
- **Preview is no longer soft.** Sheets were rasterised at 72 DPI and then scaled up by the
  zoom factor, so "Actual size" on a 96-DPI screen was a 1.33× blow-up of a 72-DPI image.
  It now rasterises at a DPI matched to how large the sheet is actually drawn (96–300),
  and re-renders when zoom moves far enough to matter.

### Phase 3 — One truth for the settings panel (2026-07-15)

**The structural fix for 0.2.0's central defect.** The Layout tab collected booklet modes,
right-to-left, signatures and creep; the engine ignored all of them; nothing could see the
gap because "the model has a field" and "the engine reads it" were unrelated facts.

- **`engine/capabilities.py`** — every setting is now classified HONOURED or NOT_IMPLEMENTED,
  and three tests enforce it: no control may target an unhonoured setting, every named path
  must exist, and **no field may escape classification**. Adding a setting to the model now
  fails the build until someone decides, in public, whether the engine honours it. Verified
  by adding a dummy field and watching it fail.
- **`ui/schema.py`** — the panel is declared, not wired: sections and controls with a
  `target`, default, description and `visible_when`. Section titles must name what they edit,
  sections stay 2–7 controls, switches may not be labelled "Enable X", segmented controls
  stay ≤4 short options — all enforced by tests rather than review.
- **Hide, never disable** — a control that can't act is removed, not greyed out. A greyed
  control still claims the feature exists.
- **`ui/panel.py`** — one `ValueStore` behind every control, which is what makes the rest
  nearly free: **undo/redo** (Ctrl+Z/Y — the Edit menu's stubs are now real),
  **per-section reset**, and **presets** (File → Save/Load Preset, readable JSON).
- **In-app help is generated from the schema** (`ui/help.py`), so it can no longer document a
  feature that doesn't exist — which is exactly what the 0.2.0 tutorial did.
- Deleted `layout_tab.py` and `sheet_tab.py` and their four hand-wired `get_settings()`
  methods. The two genuinely growable lists (preprocessors, marks) keep bespoke editors.

### Phase 5 — The layout depth the UI already promised (2026-07-15)

- **Arbitrary N-Up grids** — 1/2/4/6/8/9/16-up, or explicit rows × columns. Was hardcoded to
  2×1 and 2×2.
- **Auto-rotate** — turn a page a quarter turn when it fills its cell better, so landscape
  artwork sits on a portrait sheet without pre-rotating the file.
- **Right-to-left binding**, and **blanks in the middle** (pad at the centre spread instead of
  the end, keeping a printed back cover).
- **Signatures and perfect binding** — saddle stitch nests the whole document as one
  signature; perfect binding folds fixed-size signatures separately and gathers them, which
  changes the page order. Each signature still folds into reading order (tested).
- **Creep** — fore-edge compensation, walked linearly from the outermost sheet's shift to the
  innermost. Stated as explicit endpoints the operator measures rather than derived from a
  guessed paper caliper; negatives shift the other way.
- **Not implemented: work-and-turn and work-and-tumble.** These are press-form techniques
  that put both forms on one double-size plate, not orderings — getting them subtly wrong
  wastes plates and paper. They are removed from the model rather than left as controls that
  do nothing, and are in ROADMAP.md's backlog pending a pressman's review.

### Phase 2 — Box-aware imposition (2026-07-14)

**The headline fix.** 0.2.0 called `show_pdf_page` without a clip, so every page was imposed on
its **MediaBox**. Press-ready PDFs — the files this tool exists for — describe the finished page
with a **TrimBox** and paint artwork past it to a **BleedBox**. For those, PressReady placed the
wrong area, and printed crop marks around the wrong edge, without saying a word.

- **Source box selection** — Media / Crop / Trim / Bleed, defaulting to **Trim**. PDF defines
  TrimBox to fall back to CropBox and then MediaBox, so the new default is also correct for plain
  PDFs that carry no box information (asserted by a test).
- **Bleed** — `bleed_mm` pulls artwork beyond the chosen box and lets it spill outside the cell, so
  a slightly-off cut still lands on ink. The page does not move when bleed is added.
- **Crop marks now follow the trim rect, not the cell.** A page whose proportions differ from its
  cell is letterboxed inside it; marks drawn on the cell sat off the page edge entirely. Found while
  reasoning about boxes and fixed here.
- **Anything outside the chosen box is clipped**, so a slug mark in the media margin no longer
  reaches the press sheet.

**Architecture**
- New `engine/geometry.py` — one home for sheet/cell/box/fit maths and for `sheet_plan()`, which
  decides which page goes in which cell of which sheet. `impose.py` now only renders that plan.
- **The preview can no longer drift from the output.** It used to re-derive cell geometry from the
  project while displaying a separately-imposed PDF: two opinions about one layout. `impose_to_temp`
  now returns an `ImposeResult` carrying the geometry the run actually used, and the overlay
  describes *that*. Deleted `compute_cells()` and its duplicate maths.
- `LayoutSettings` gained `rows`/`cols` (groundwork for arbitrary N-Up grids).

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
- Version single-sourced from `pressready/__init__.py`. `pyproject.toml` reads it dynamically, the
  About dialog no longer hardcodes it, and `build_msix.ps1` reads it and **stamps it into the
  staged manifest** — its `$appVersion` was previously computed and then never used, so the MSIX
  silently took whatever the checked-in `AppxManifest.xml` said and bumping the script did nothing.

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

## [0.2.0] — 2026-02-19

_Published at the time as **v2.0.0**, renumbered to 0.2.0 on 2026-07-15 when the project moved
to 0.x versioning. The code and the released binaries are unchanged — only the label. Their
filenames still read `2.0.0`, and the MSIX still declares `2.0.0.0` internally, because they
are the original files._

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
