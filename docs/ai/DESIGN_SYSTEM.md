# Design system — PressReady

Every colour, radius, size and the whole global stylesheet live in **`pressready/ui/theme.py`**.
Nothing else defines a colour. There are no .qss files and no styling assets.
The visual language follows the Toolcraft study — see `REFERENCE_STUDY.md` §2.

## Tokens (`ui/theme.py`)

Neutrals are written in **OKLCH** and converted to hex at import, because Qt stylesheets
have no `oklch()` or `color-mix()`. Keep editing them in OKLCH: equal lightness steps look
equal there, which is the whole point. `theme.oklch()` and `theme.mix()` do the conversion
(verified exact: `oklch(0.269)` → `#262626`, matching Toolcraft's own literal).

| Token | Use |
|-------|-----|
| `ACCENT` `#D07B24` + `_HOVER`/`_PRESS` | The one accent. Brand orange, kept deliberately (see DECISIONS) |
| `BG` / `SURFACE` / `RAISED` / `INPUT_BG` | Window / settings panel / bars & headers / fields |
| `BORDER`, `BORDER_SOFT` | Hairlines and dividers |
| `FG` / `FG_MUTED` / `FG_FAINT` | Primary / secondary / tertiary text |
| `HOVER_WASH`, `SELECTED_WASH`, `SCROLL_THUMB` | Computed washes — don't hardcode equivalents |
| `DESTRUCTIVE` | Preflight errors only |
| `OVERLAY` `#FF0090` | Preview overlays only. **Never printed** — deliberately outside the palette |

Metrics: radius 2/4/6/8/12 · text 11/12/13/14/16 · spacing 4/6/8/12/16/24 ·
`SECTION_HEADER_H` 36 · `PANEL_W` 320 · 4px scrollbars, 44px min thumb.

## Rules
- **One accent.** Everything interactive highlights with `ACCENT`. Magenta is reserved for
  preview overlays; a second accent would break the association.
- **Printed marks are black/grey only** (`engine/marks.py`) — those go to press. The colour
  bar is the sole exception, and it is *meant* to be ink.
- **Hide, never disable.** A control that can't act is removed via `visible_when`, not greyed
  out. See DECISIONS — this is the rule that answers 0.2.0's central defect.
- **Sections name what they edit** (`Booklet`, `Bleed`, `Margins`) — never `Settings`,
  `Options`, `General`. Enforced by `tests/test_capabilities.py`.
- Switch labels never start with "Enable" — the switch already says on/off. Also enforced.
- Segmented controls: full-width, ≤4 options, ≤14 chars each. Enforced.
- Icons are **drawn in code with QPainter** (`_ico_*` in `main_window.py`) — no icon files at
  runtime except the app icon in `assets/icons/`. 1.0–1.5px pens, `_STROKE`/`_FILL`.
- Font: Segoe UI (`theme.FONT_FAMILY`) — the platform stand-in for Toolcraft's Inter.
- The in-app help restates the palette inline but **reads it from `theme`** (`ui/help.py`),
  so tokens only change in one place.
