"""
UI icons — the Lucide icon set (https://lucide.dev), rendered through Qt.

Lucide is ISC-licensed; see NOTICE. Each icon below is the *verbatim* inner geometry
of the corresponding Lucide SVG (v1.24.0) — pulled from the `lucide-static` package,
not redrawn — so they match the published icons exactly. They are wrapped at render
time in an <svg> with the theme stroke colour and rasterised with QtSvg.

Add an icon: copy the inner markup of its Lucide SVG into _GEOMETRY under a new key.
"""

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QIcon, QImage, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

from laydown.ui import theme as t

# Verbatim inner geometry of each Lucide icon (v1.24.0, ISC). Key = our name.
_GEOMETRY = {
    'columns_1': '<rect width="12" height="20" x="6" y="2" rx="2" />',
    'columns_2': '<rect width="18" height="18" x="3" y="3" rx="2" /> <path d="M12 3v18" />',
    'columns_4': '<path d="M12 3v18" /> <path d="M3 12h18" /> <rect x="3" y="3" width="18" height="18" rx="2" />',
    'zoom_in': '<circle cx="11" cy="11" r="8" /> <line x1="21" x2="16.65" y1="21" y2="16.65" /> <line x1="11" x2="11" y1="8" y2="14" /> <line x1="8" x2="14" y1="11" y2="11" />',
    'zoom_out': '<circle cx="11" cy="11" r="8" /> <line x1="21" x2="16.65" y1="21" y2="16.65" /> <line x1="8" x2="14" y1="11" y2="11" />',
    'fit_width': '<path d="m18 8 4 4-4 4" /> <path d="M2 12h20" /> <path d="m6 8-4 4 4 4" />',
    'fit_page': '<path d="M8 3H5a2 2 0 0 0-2 2v3" /> <path d="M21 8V5a2 2 0 0 0-2-2h-3" /> <path d="M3 16v3a2 2 0 0 0 2 2h3" /> <path d="M16 21h3a2 2 0 0 0 2-2v-3" />',
    'actual_size': '<rect width="20" height="16" x="2" y="4" rx="2" /> <path d="M12 9v11" /> <path d="M2 9h13a2 2 0 0 1 2 2v9" />',
    'tab_source': '<path d="M4 11V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.706.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-1" /> <path d="M14 2v5a1 1 0 0 0 1 1h5" /> <path d="M2 15h10" /> <path d="m9 18 3-3-3-3" />',
    'tab_layout': '<rect width="18" height="7" x="3" y="3" rx="1" /> <rect width="9" height="7" x="3" y="14" rx="1" /> <rect width="5" height="7" x="16" y="14" rx="1" />',
    'tab_sheet': '<path d="M21.3 15.3a2.4 2.4 0 0 1 0 3.4l-2.6 2.6a2.4 2.4 0 0 1-3.4 0L2.7 8.7a2.41 2.41 0 0 1 0-3.4l2.6-2.6a2.41 2.41 0 0 1 3.4 0Z" /> <path d="m14.5 12.5 2-2" /> <path d="m11.5 9.5 2-2" /> <path d="m8.5 6.5 2-2" /> <path d="m17.5 15.5 2-2" />',
    'tab_marks': '<path d="M6 2v14a2 2 0 0 0 2 2h14" /> <path d="M18 22V8a2 2 0 0 0-2-2H2" />',
    'generate': '<path d="M4.226 20.925A2 2 0 0 0 6 22h12a2 2 0 0 0 2-2V8a2.4 2.4 0 0 0-.706-1.706l-3.588-3.588A2.4 2.4 0 0 0 14 2H6a2 2 0 0 0-2 2v3.127" /> <path d="M14 2v5a1 1 0 0 0 1 1h5" /> <path d="m5 11-3 3" /> <path d="m5 17-3-3h10" />',

    # Menu icons (added 0.4.1)
    'open': '<path d="m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2" />',
    'recent': '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" /> <path d="M3 3v5h5" /> <path d="M12 7v5l4 2" />',
    'close': '<path d="M18 6 6 18" /> <path d="m6 6 12 12" />',
    'save_preset': '<path d="M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" /> <path d="M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7" /> <path d="M7 3v4a1 1 0 0 0 1 1h7" />',
    'load_preset': '<path d="M2 9V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H20a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-1" /> <path d="M2 13h10" /> <path d="m9 16 3-3-3-3" />',
    'quit': '<path d="m16 17 5-5-5-5" /> <path d="M21 12H9" /> <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />',
    'undo': '<path d="M9 14 4 9l5-5" /> <path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5a5.5 5.5 0 0 1-5.5 5.5H11" />',
    'redo': '<path d="m15 14 5-5-5-5" /> <path d="M20 9H9.5A5.5 5.5 0 0 0 4 14.5A5.5 5.5 0 0 0 9.5 20H13" />',
    'reset': '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" /> <path d="M3 3v5h5" />',
    'tutorials': '<path d="M12 7v14" /> <path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z" />',
    'preflight': '<rect width="8" height="4" x="8" y="2" rx="1" ry="1" /> <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" /> <path d="m9 14 2 2 4-4" />',
    'sysdir': '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" />',
    'about': '<circle cx="12" cy="12" r="10" /> <path d="M12 16v-4" /> <path d="M12 8h.01" />',
}

# Lucide's canvas and stroke conventions — do not change per-icon, that's the point.
_VIEWBOX = 24
_STROKE_WIDTH = 2.0

_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vb} {vb}" fill="none" '
    'stroke="{color}" stroke-width="{sw}" stroke-linecap="round" '
    'stroke-linejoin="round">{inner}</svg>'
)


def lucide(name: str, size: int = 22, color: str | None = None,
           stroke_width: float = _STROKE_WIDTH) -> QIcon:
    """A Lucide icon as a QIcon, stroked in *color* (defaults to muted foreground)."""
    if name not in _GEOMETRY:
        raise KeyError(f"no Lucide icon registered as {name!r}")
    svg = _SVG.format(vb=_VIEWBOX, color=color or t.FG_MUTED,
                      sw=stroke_width, inner=_GEOMETRY[name]).encode("utf-8")

    # Render at 3x for crisp edges on any DPI, then tag the pixmap's ratio so Qt
    # draws it at the logical size.
    scale = 3
    renderer = QSvgRenderer(svg)
    image = QImage(size * scale, size * scale, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size * scale, size * scale))
    painter.end()

    pixmap = QPixmap.fromImage(image)
    pixmap.setDevicePixelRatio(scale)
    return QIcon(pixmap)


def names() -> tuple:
    """Every registered icon name — used by the test that guards the set."""
    return tuple(_GEOMETRY)
