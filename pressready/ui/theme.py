"""
Design tokens — one place for every colour, radius, size and the global stylesheet.

The visual language follows the Toolcraft study (docs/ai/REFERENCE_STUDY.md): a dark
neutral ramp defined in OKLCH, a small radius scale, hairline 4px scrollbars, focus
rings only for keyboard users, and generous, consistent control padding.

Qt stylesheets have no ``oklch()`` or ``color-mix()``, so the neutrals are written
here in OKLCH — the space they were designed in, where equal lightness steps look
equal — and converted to hex at import. Keep editing them in OKLCH; the conversion
is exact and cheap.

The accent stays PressReady orange rather than Toolcraft's blue: it is the product's
identity and is already baked into the app icon and MSIX tiles. What is borrowed is
the structure, density and control anatomy, not the branding.
"""

from math import cos, pi, sin


# ── OKLCH → sRGB ─────────────────────────────────────

def _srgb_encode(u: float) -> int:
    u = max(0.0, min(1.0, u))
    u = 1.055 * (u ** (1 / 2.4)) - 0.055 if u > 0.0031308 else 12.92 * u
    return round(max(0.0, min(1.0, u)) * 255)


def oklch(lightness: float, chroma: float = 0.0, hue: float = 0.0) -> str:
    """An OKLCH colour as a Qt-usable ``#RRGGBB`` string."""
    h = hue * pi / 180.0
    a, b = chroma * cos(h), chroma * sin(h)

    l_ = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (lightness - 0.0894841775 * a - 1.2914855480 * b) ** 3

    r = 4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_
    g = -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_
    bl = -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_
    return "#%02X%02X%02X" % (_srgb_encode(r), _srgb_encode(g), _srgb_encode(bl))


def mix(colour: str, over: str, amount: float) -> str:
    """Blend *amount* of ``colour`` over ``over`` — stands in for CSS color-mix()."""
    def parts(c):
        c = c.lstrip("#")
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    a, b = parts(colour), parts(over)
    return "#%02X%02X%02X" % tuple(
        round(x * amount + y * (1 - amount)) for x, y in zip(a, b)
    )


# ── colour ───────────────────────────────────────────

# Brand. Kept from v2 — see module docstring.
ACCENT = "#D07B24"
ACCENT_HOVER = "#BC6F20"
ACCENT_PRESS = "#A8631C"
ACCENT_FG = "#FFFFFF"

# Neutrals, in the space they were designed in.
BG = oklch(0.145)               # window
SURFACE = oklch(0.185)          # settings panel
RAISED = oklch(0.225)           # bars, headers
INPUT_BG = oklch(0.269)         # fields
BORDER = oklch(0.311, 0.013, 279.19)
BORDER_SOFT = oklch(0.269)
FG = oklch(0.977)               # primary text
FG_MUTED = oklch(0.708)         # secondary text
FG_FAINT = oklch(0.556)         # tertiary / disabled
RING = oklch(0.556)

DESTRUCTIVE = "#F04438"
SCROLL_THUMB = mix(FG, SURFACE, 0.14)
SCROLL_THUMB_HOVER = mix(FG, SURFACE, 0.26)
HOVER_WASH = mix(FG, SURFACE, 0.06)
SELECTED_WASH = mix(FG, SURFACE, 0.10)

# Preview overlays only — never printed. Deliberately outside the palette so it can
# never be mistaken for product ink.
OVERLAY = "#FF0090"


# ── metrics ──────────────────────────────────────────

RADIUS_XS, RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_XL = 2, 4, 6, 8, 12

TEXT_2XS, TEXT_XS, TEXT_SM, TEXT_MD, TEXT_LG = 11, 12, 13, 14, 16

SPACE_1, SPACE_2, SPACE_3, SPACE_4, SPACE_5, SPACE_6 = 4, 6, 8, 12, 16, 24

SECTION_HEADER_H = 36     # Toolcraft's collapsible header row
SECTION_TOP_PAD = 8
SECTION_BOTTOM_PAD = 24
CONTROL_H = 28
PANEL_W = 320
SCROLLBAR_W = 4
SCROLL_THUMB_MIN = 44
FONT_FAMILY = "Segoe UI"  # Toolcraft ships Inter; this is the platform equivalent


# ── the global stylesheet ────────────────────────────

def stylesheet() -> str:
    """
    The whole application's QSS.

    Focus rings are attached to a ``keyboardFocus`` property rather than ``:focus``,
    so clicking a field doesn't light it up but tabbing to it does — Toolcraft's
    keyboard-only focus rule. ``ui/panel.py`` maintains the property.
    """
    return f"""
QWidget {{ color: {FG}; font-family: "{FONT_FAMILY}"; font-size: {TEXT_SM}px; }}
QMainWindow, QDialog {{ background: {BG}; }}

/* menu */
QMenuBar {{ background: {RAISED}; color: {FG_MUTED}; border-bottom: 1px solid {BORDER};
            padding: 2px 0; }}
QMenuBar::item {{ padding: 5px 10px; background: transparent; border-radius: {RADIUS_SM}px; }}
QMenuBar::item:selected {{ background: {HOVER_WASH}; color: {FG}; }}
QMenu {{ background: {RAISED}; color: {FG}; border: 1px solid {BORDER};
         border-radius: {RADIUS_MD}px; padding: {SPACE_1}px; }}
QMenu::item {{ padding: 6px 24px 6px 12px; border-radius: {RADIUS_SM}px; }}
QMenu::item:selected {{ background: {ACCENT}; color: {ACCENT_FG}; }}
QMenu::item:disabled {{ color: {FG_FAINT}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: {SPACE_1}px {SPACE_2}px; }}

QStatusBar {{ background: {BG}; color: {FG_MUTED}; border-top: 1px solid {BORDER}; }}
QStatusBar::item {{ border: none; }}
QLabel {{ background: transparent; }}
QToolTip {{ background: {RAISED}; color: {FG}; border: 1px solid {BORDER};
            border-radius: {RADIUS_SM}px; padding: 4px 8px; }}

/* fields */
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {{
    background: {INPUT_BG}; color: {FG}; border: 1px solid {BORDER};
    border-radius: {RADIUS_MD}px; padding: 4px 8px; min-height: {CONTROL_H - 10}px;
    selection-background-color: {ACCENT}; selection-color: {ACCENT_FG};
}}
QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QLineEdit:hover {{
    border-color: {mix(FG, BORDER, 0.25)};
}}
QLineEdit[keyboardFocus="true"], QComboBox[keyboardFocus="true"],
QSpinBox[keyboardFocus="true"], QDoubleSpinBox[keyboardFocus="true"] {{
    border-color: {ACCENT}; outline: none;
}}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox QAbstractItemView {{
    background: {RAISED}; color: {FG}; border: 1px solid {BORDER};
    border-radius: {RADIUS_MD}px; padding: {SPACE_1}px; outline: none;
    selection-background-color: {ACCENT}; selection-color: {ACCENT_FG};
}}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background: transparent; border: none; width: 14px;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{ background: {HOVER_WASH}; }}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
    color: {FG_FAINT}; background: {mix(INPUT_BG, BG, 0.5)};
}}

/* buttons */
QPushButton {{
    background: {INPUT_BG}; color: {FG}; border: 1px solid {BORDER};
    border-radius: {RADIUS_MD}px; padding: 5px 12px; min-height: {CONTROL_H - 10}px;
}}
QPushButton:hover {{ background: {mix(FG, INPUT_BG, 0.08)}; }}
QPushButton:pressed {{ background: {mix(BG, INPUT_BG, 0.4)}; }}
QPushButton:disabled {{ color: {FG_FAINT}; background: {mix(INPUT_BG, BG, 0.5)};
                        border-color: {BORDER_SOFT}; }}
QPushButton[accent="true"] {{ background: {ACCENT}; color: {ACCENT_FG}; border: none;
                             font-weight: 600; padding: 7px 16px; }}
QPushButton[accent="true"]:hover {{ background: {ACCENT_HOVER}; }}
QPushButton[accent="true"]:pressed {{ background: {ACCENT_PRESS}; }}
QPushButton[accent="true"]:disabled {{ background: {mix(INPUT_BG, BG, 0.5)}; color: {FG_FAINT}; }}

/* checkable */
QCheckBox, QRadioButton {{ spacing: {SPACE_2}px; background: transparent; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 15px; height: 15px; border: 1px solid {mix(FG, BORDER, 0.2)}; background: {INPUT_BG};
}}
QCheckBox::indicator {{ border-radius: {RADIUS_XS}px; }}
QRadioButton::indicator {{ border-radius: 8px; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background: {ACCENT}; border-color: {ACCENT};
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: {ACCENT}; }}

/* containers */
QScrollArea {{ border: none; background: transparent; }}
QSplitter::handle {{ background: {BORDER}; }}
QProgressBar {{ background: {INPUT_BG}; border: none; border-radius: {RADIUS_SM}px;
                text-align: center; color: {FG}; height: 6px; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: {RADIUS_SM}px; }}
QTextBrowser {{ background: {BG}; color: {FG}; border: 1px solid {BORDER};
                border-radius: {RADIUS_MD}px; }}
QListWidget {{ background: {mix(BG, SURFACE, 0.5)}; color: {FG}; border: 1px solid {BORDER};
               border-radius: {RADIUS_MD}px; outline: none; padding: 2px; }}
QListWidget::item {{ padding: 5px 8px; border-radius: {RADIUS_SM}px; }}
QListWidget::item:selected {{ background: {ACCENT}; color: {ACCENT_FG}; }}
QListWidget::item:hover:!selected {{ background: {HOVER_WASH}; }}

/* hairline scrollbars */
QScrollBar:vertical {{ background: transparent; width: {SCROLLBAR_W + 4}px; margin: 0; }}
QScrollBar:horizontal {{ background: transparent; height: {SCROLLBAR_W + 4}px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {SCROLL_THUMB}; border-radius: {SCROLLBAR_W // 2}px;
    min-height: {SCROLL_THUMB_MIN}px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {SCROLL_THUMB}; border-radius: {SCROLLBAR_W // 2}px;
    min-width: {SCROLL_THUMB_MIN}px; margin: 2px; }}
QScrollBar::handle:hover {{ background: {SCROLL_THUMB_HOVER}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
"""
