# Design system — PressReady dark theme

All theming lives in **`pressready/ui/main_window.py`** as module constants + one global
Qt stylesheet (`_DARK_STYLE`). There are no .qss files or external assets for styling.

## Tokens
| Token | Value | Use |
|-------|-------|-----|
| `_ACCENT` | `#D07B24` (orange) | Primary actions, focus borders, selections, headings |
| `_ACCENT_HOVER` / `_ACCENT_PRESS` | `#BC6F20` / `#A8631C` | Generate-button states |
| `_BG` / `_BG2` / `_BG3` | `#1e1e1e` / `#252526` / `#2d2d2d` | Window / panel / bars |
| `_BG_INPUT` | `#3c3c3c` | All input fields |
| `_BORDER` | `#3e3e42` | Separators, group boxes |
| `_TEXT` / `_TEXT_DIM` | `#d4d4d4` / `#888` | Body / secondary text |
| `MAGENTA` (`preview_panel.py`) | `#FF0090` | Preview-only overlays (numbers, frames, tops) |

## Rules
- **One accent color.** Everything interactive highlights with `_ACCENT`; don't introduce
  a second accent. Magenta is reserved for preview overlays (never printed output).
- **Printed marks are black/gray only** (`engine/marks.py`) — marks go to press.
- Icons are **drawn in code with QPainter** (`_ico_*` factories) — no icon image files at
  runtime except the app icon (`assets/icons/`). New toolbar/tab icons follow that pattern:
  1.0–1.5 px pens, `_CLR` gray-blue strokes, `_FILL` fills.
- Font: Segoe UI 9pt app-wide (set in `__main__.py`); tutorials/about HTML restate the
  palette inline — update those when tokens change.
- Right settings panel is fixed 310 px; left column flexes.
