"""
Multi-sheet scrollable preview canvas.

Renders ALL imposed sheets and displays them in a scrollable grid.
Supports 1/2/4-column layout, zoom, fit-to-width/page, and overlays.
"""

import os
from typing import Optional, List
from dataclasses import dataclass

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea,
    QGridLayout, QSizePolicy, QApplication,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPixmap, QImage, QFont, QPainter, QPen, QColor

import fitz

from pressready.engine.data_model import Project, LayoutType
from pressready.engine.utils import mm_to_pt, parse_page_range
from pressready.engine.impose import impose_to_temp, booklet_page_order

MAGENTA = QColor(255, 0, 144)


# ── cell geometry for overlays ───────────────────────


@dataclass
class CellInfo:
    x0: float
    y0: float
    x1: float
    y1: float
    page_num: int  # 1-based, 0 = blank


def compute_cells(project: Project, sheet_idx: int) -> List[CellInfo]:
    if not project.source_pdf_path:
        return []
    try:
        doc = fitz.open(project.source_pdf_path)
        total = len(doc)
        doc.close()
    except Exception:
        return []

    expr = project.layout.page_range.strip()
    try:
        page_indices = parse_page_range(expr, total) if expr else list(range(total))
    except ValueError:
        page_indices = list(range(total))

    num_src = len(page_indices)
    if num_src == 0:
        return []

    w_mm, h_mm = project.sheet.sheet_size_mm()
    sw, sh = mm_to_pt(w_mm), mm_to_pt(h_mm)
    s = project.sheet
    ml, mr = mm_to_pt(s.margin_left_mm), mm_to_pt(s.margin_right_mm)
    mt, mb = mm_to_pt(s.margin_top_mm), mm_to_pt(s.margin_bottom_mm)
    lay = project.layout

    if lay.layout_type == LayoutType.BOOKLET:
        gh = mm_to_pt(lay.gutter_h_mm)
        cw = (sw - ml - mr - gh) / 2
        ch = sh - mt - mb
        order = booklet_page_order(num_src)
        if sheet_idx >= len(order):
            return []
        lp, rp = order[sheet_idx]
        return [
            CellInfo(ml, mt, ml + cw, mt + ch,
                     (page_indices[lp] + 1) if lp >= 0 else 0),
            CellInfo(ml + cw + gh, mt, ml + 2 * cw + gh, mt + ch,
                     (page_indices[rp] + 1) if rp >= 0 else 0),
        ]

    nup = lay.nup
    cols = 2
    rows = 1 if nup == 2 else 2
    gh = mm_to_pt(lay.gutter_h_mm)
    gv = mm_to_pt(lay.gutter_v_mm)
    cw = (sw - ml - mr - (cols - 1) * gh) / cols
    ch = (sh - mt - mb - (rows - 1) * gv) / rows

    cells = []
    for ci in range(nup):
        idx = sheet_idx * nup + ci
        if idx >= num_src:
            break
        col = ci % cols
        row = ci // cols
        x0 = ml + col * (cw + gh)
        y0 = mt + row * (ch + gv)
        cells.append(CellInfo(x0, y0, x0 + cw, y0 + ch, page_indices[idx] + 1))
    return cells


def draw_overlays(
    pixmap: QPixmap, cells: List[CellInfo], scale: float,
    show_tops: bool, show_numbers: bool, show_frames: bool, show_previews: bool,
) -> QPixmap:
    if not cells:
        return pixmap
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    for c in cells:
        px0, py0 = c.x0 * scale, c.y0 * scale
        pw, ph = (c.x1 - c.x0) * scale, (c.y1 - c.y0) * scale
        rect = QRectF(px0, py0, pw, ph)

        if not show_previews:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(245, 245, 245))
            painter.drawRect(rect)

        if show_frames and c.page_num > 0:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(MAGENTA, max(1.0, scale * 0.5)))
            painter.drawRect(rect)

        if show_tops and c.page_num > 0:
            painter.setPen(QPen(MAGENTA, max(1.5, scale * 0.7)))
            painter.drawLine(QPointF(px0, py0), QPointF(px0 + pw, py0))
            cx = px0 + pw / 2
            painter.drawLine(QPointF(cx, py0), QPointF(cx, py0 + min(20 * scale / 1.5, ph * 0.06)))

        if show_numbers and c.page_num > 0:
            fs = max(14, int(min(pw, ph) * 0.18))
            f = QFont("Segoe UI", fs)
            f.setBold(True)
            painter.setFont(f)
            painter.setPen(MAGENTA)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(c.page_num))

    painter.end()
    return pixmap


# ── worker: render ALL sheets ────────────────────────


class _RenderWorker(QThread):
    done = pyqtSignal(list)  # List[QPixmap]
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project: Optional[Project] = None
        self.dpi: int = 72
        self.show_tops = False
        self.show_numbers = True
        self.show_frames = True
        self.show_previews = True
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        self._cancel = False
        tmp_path = None
        try:
            tmp_path, _ = impose_to_temp(self.project)
            doc = fitz.open(tmp_path)
            total = len(doc)
            mat = fitz.Matrix(self.dpi / 72.0, self.dpi / 72.0)
            scale = self.dpi / 72.0
            pixmaps = []

            for i in range(total):
                if self._cancel:
                    doc.close()
                    return
                page = doc[i]
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = QImage(pix.samples, pix.width, pix.height, pix.stride,
                             QImage.Format.Format_RGB888)
                pm = QPixmap.fromImage(img)
                cells = compute_cells(self.project, i)
                pm = draw_overlays(pm, cells, scale,
                                   self.show_tops, self.show_numbers,
                                   self.show_frames, self.show_previews)
                pixmaps.append(pm)

            doc.close()
            if not self._cancel:
                self.done.emit(pixmaps)
        except Exception as e:
            if not self._cancel:
                self.error.emit(str(e))
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass


# ── main canvas widget ───────────────────────────────


class SheetCanvas(QScrollArea):
    """Scrollable multi-sheet preview with zoom and column controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project: Optional[Project] = None
        self._pixmaps: List[QPixmap] = []
        self._columns = 2
        self._zoom = 0.0  # 0 = auto-fit on first render
        self._base_dpi = 72
        self._sheet_widgets: list = []

        self._show_tops = False
        self._show_numbers = True
        self._show_frames = True
        self._show_previews = True

        self._worker = _RenderWorker(self)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)
        self._debounce.timeout.connect(self._do_render)

        self._setup_ui()

    def _setup_ui(self):
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea { border: none; }")
        self._content = QWidget()
        self._content.setStyleSheet("background: #1e1e1e;")
        self.setWidget(self._content)
        self._grid = QGridLayout(self._content)
        self._grid.setSpacing(16)
        self._grid.setContentsMargins(16, 16, 16, 16)
        self._show_placeholder()

    def _show_placeholder(self):
        self._clear_grid()
        lbl = QLabel("Open a PDF to get started\n\nFile \u2192 Open PDF  (Ctrl+O)\nor drag and drop a PDF here")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #666; font-size: 15px; padding: 60px;")
        self._grid.addWidget(lbl, 0, 0)

    def _clear_grid(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        self._sheet_widgets.clear()

    # ── public API ───────────────────────────────

    def update_project(self, project: Project):
        self._project = project
        self._debounce.start()

    def set_columns(self, n: int):
        self._columns = n
        self._rebuild_display()

    def set_overlays(self, show_tops, show_numbers, show_frames, show_previews):
        self._show_tops = show_tops
        self._show_numbers = show_numbers
        self._show_frames = show_frames
        self._show_previews = show_previews
        if self._project:
            self._debounce.start()

    def clear_all(self):
        self._worker.cancel()
        self._worker.wait()
        self._project = None
        self._pixmaps.clear()
        self._show_placeholder()

    def zoom_in(self):
        if self._zoom <= 0:
            self._zoom = 1.0
        self._zoom = min(4.0, self._zoom * 1.25)
        self._rebuild_display()

    def zoom_out(self):
        if self._zoom <= 0:
            self._zoom = 1.0
        self._zoom = max(0.15, self._zoom / 1.25)
        self._rebuild_display()

    def fit_width(self):
        if not self._pixmaps:
            return
        avail = self.viewport().width() - self._grid.spacing() * (self._columns + 1) - 40
        per_col = avail / self._columns
        bw = self._pixmaps[0].width()
        self._zoom = per_col / bw if bw > 0 else 1.0
        self._rebuild_display()

    def fit_page(self):
        if not self._pixmaps:
            return
        vp = self.viewport()
        aw = (vp.width() - 60) / self._columns
        ah = vp.height() - 70
        bw = self._pixmaps[0].width()
        bh = self._pixmaps[0].height()
        self._zoom = min(aw / bw if bw else 1, ah / bh if bh else 1)
        self._rebuild_display()

    def actual_size(self):
        try:
            sdpi = QApplication.primaryScreen().logicalDotsPerInch()
        except Exception:
            sdpi = 96
        self._zoom = sdpi / self._base_dpi
        self._rebuild_display()

    def get_zoom_percent(self) -> int:
        z = self._zoom if self._zoom > 0 else 1.0
        return int(z * 100)

    # ── rendering ────────────────────────────────

    def _do_render(self):
        if not self._project or not self._project.source_pdf_path:
            return
        self._worker.cancel()
        self._worker.wait()
        self._worker.project = self._project
        self._worker.dpi = self._base_dpi
        self._worker.show_tops = self._show_tops
        self._worker.show_numbers = self._show_numbers
        self._worker.show_frames = self._show_frames
        self._worker.show_previews = self._show_previews
        self._worker.start()

    def _on_done(self, pixmaps: list):
        self._pixmaps = pixmaps
        if self._zoom <= 0:
            self._rebuild_display()
            QTimer.singleShot(50, self.fit_width)
        else:
            self._rebuild_display()

    def _on_error(self, msg: str):
        self._clear_grid()
        lbl = QLabel(f"Render error:\n{msg}")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #ff6b6b; font-size: 13px; padding: 40px;")
        self._grid.addWidget(lbl, 0, 0)

    # ── display ──────────────────────────────────

    def _rebuild_display(self):
        self._clear_grid()
        if not self._pixmaps:
            self._show_placeholder()
            return

        zoom = max(0.1, self._zoom) if self._zoom > 0 else 1.0
        cols = self._columns

        for i, pm in enumerate(self._pixmaps):
            row = i // cols
            col = i % cols

            container = QWidget()
            container.setStyleSheet("background: transparent;")
            vbox = QVBoxLayout(container)
            vbox.setContentsMargins(4, 4, 4, 6)
            vbox.setSpacing(4)

            lbl = QLabel()
            target_w = max(60, int(pm.width() * zoom))
            scaled = pm.scaledToWidth(target_w, Qt.TransformationMode.SmoothTransformation)
            lbl.setPixmap(scaled)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("border: 1px solid #3e3e42;")
            vbox.addWidget(lbl)

            num = QLabel(str(i + 1))
            num.setAlignment(Qt.AlignmentFlag.AlignCenter)
            num.setStyleSheet("color: #888; font-size: 11px; background: transparent;")
            vbox.addWidget(num)

            self._grid.addWidget(container, row, col,
                                 Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
            self._sheet_widgets.append(container)

    # ── cleanup ──────────────────────────────────

    def cleanup(self):
        self._worker.cancel()
        self._worker.wait()
