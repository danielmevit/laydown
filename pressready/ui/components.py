"""
The control kit — the small set of widgets every settings section is built from.

Recreated from the Toolcraft study (docs/ai/REFERENCE_STUDY.md) in Qt: a 36px
collapsible section header carrying a per-section reset, a real switch rather than a
checkbox, a full-width segmented control for short finite choices, and label-above
rows. None of it is ported code — Toolcraft is React and Tailwind — only the anatomy.
"""

from typing import Any, Callable, List, Optional, Tuple

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QAbstractButton, QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from pressready.ui import theme as t


class Switch(QAbstractButton):
    """A binary toggle. Its label says what it does, never 'Enable X'."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(34, 20)

    def sizeHint(self) -> QSize:
        return QSize(34, 20)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        on = self.isChecked()

        track = QRectF(0, 2, 34, 16)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(t.ACCENT if on else t.INPUT_BG))
        p.drawRoundedRect(track, 8, 8)
        if not on:
            p.setPen(QPen(QColor(t.BORDER), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(track.adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(t.ACCENT_FG if on else t.FG_MUTED))
        p.drawEllipse(QPointF(24.0 if on else 10.0, 10.0), 6.0, 6.0)
        p.end()


class Segmented(QWidget):
    """
    A full-width finite choice. Never sits beside another control.

    Kept to short option sets; the schema test enforces at most four options and
    fourteen characters each, because past that the cells clip and a select is right.
    """

    changed = pyqtSignal(object)

    def __init__(self, options: List[Tuple[Any, str]], parent=None):
        super().__init__(parent)
        self._values = [value for value, _ in options]
        self.setFixedHeight(t.CONTROL_H)
        self.setStyleSheet(
            f"Segmented {{ background: {t.INPUT_BG}; border: 1px solid {t.BORDER};"
            f"             border-radius: {t.RADIUS_MD}px; }}"
        )
        row = QHBoxLayout(self)
        row.setContentsMargins(2, 2, 2, 2)
        row.setSpacing(2)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for index, (_, text) in enumerate(options):
            button = QPushButton(text)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(
                f"QPushButton {{ background: transparent; border: none; color: {t.FG_MUTED};"
                f"               border-radius: {t.RADIUS_SM}px; padding: 3px 6px;"
                f"               font-size: {t.TEXT_XS}px; min-height: 0; }}"
                f"QPushButton:hover {{ color: {t.FG}; background: {t.HOVER_WASH}; }}"
                f"QPushButton:checked {{ background: {t.RAISED}; color: {t.FG};"
                f"                       font-weight: 600; }}"
            )
            self._group.addButton(button, index)
            row.addWidget(button, 1)
        self._group.idClicked.connect(
            lambda i: self.changed.emit(self._values[i])
        )

    def value(self) -> Any:
        button = self._group.checkedButton()
        return self._values[self._group.id(button)] if button else None

    def set_value(self, value: Any) -> None:
        if value not in self._values:
            return
        button = self._group.button(self._values.index(value))
        if button:
            button.blockSignals(True)
            button.setChecked(True)
            button.blockSignals(False)


class SectionHeader(QWidget):
    """
    The 36px row that titles a section, collapses it, and resets it.

    Reset restores only this section's targets to their schema defaults, which is
    what makes experimenting cheap: you can always get one group back without
    losing the rest of the setup.
    """

    toggled = pyqtSignal(bool)
    reset_clicked = pyqtSignal()

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._expanded = True
        self.setFixedHeight(t.SECTION_HEADER_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        row = QHBoxLayout(self)
        row.setContentsMargins(t.SPACE_3, 0, t.SPACE_2, 0)
        row.setSpacing(t.SPACE_2)

        self._chevron = QLabel("▾")
        self._chevron.setStyleSheet(f"color: {t.FG_FAINT}; font-size: {t.TEXT_2XS}px;")
        row.addWidget(self._chevron)

        self._title = QLabel(title)
        self._title.setStyleSheet(
            f"color: {t.FG}; font-size: {t.TEXT_SM}px; font-weight: 600;")
        row.addWidget(self._title)
        row.addStretch(1)

        self._reset = QPushButton("Reset")
        self._reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset.setToolTip("Restore this section to its defaults")
        self._reset.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; color: {t.FG_FAINT};"
            f"               font-size: {t.TEXT_2XS}px; padding: 2px 6px; min-height: 0;"
            f"               border-radius: {t.RADIUS_SM}px; }}"
            f"QPushButton:hover {{ color: {t.FG}; background: {t.HOVER_WASH}; }}"
        )
        self._reset.clicked.connect(self.reset_clicked.emit)
        row.addWidget(self._reset)

    def mousePressEvent(self, event):
        if not self._reset.geometry().contains(event.pos()):
            self.set_expanded(not self._expanded)
        super().mousePressEvent(event)

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self._chevron.setText("▾" if expanded else "▸")
        self.toggled.emit(expanded)

    def is_expanded(self) -> bool:
        return self._expanded


class FieldRow(QWidget):
    """A labelled control. The label sits above, so long labels never squeeze the field."""

    def __init__(self, label: str, widget: QWidget, description: str = "", parent=None):
        super().__init__(parent)
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(t.SPACE_1)

        if label:
            caption = QLabel(label)
            caption.setStyleSheet(f"color: {t.FG_MUTED}; font-size: {t.TEXT_XS}px;")
            if description:
                caption.setToolTip(description)
            column.addWidget(caption)
        column.addWidget(widget)
        if description:
            widget.setToolTip(description)
        self.widget = widget


class InlineRow(QWidget):
    """
    Two short related controls side by side, each taking half the width.

    Only for genuinely paired values (margins, gutters). Segmented controls and
    anything with a long label stack instead.
    """

    def __init__(self, left: QWidget, right: QWidget, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(t.SPACE_3)
        row.addWidget(left, 1)
        row.addWidget(right, 1)


def divider() -> QFrame:
    line = QFrame()
    line.setFixedHeight(1)
    line.setStyleSheet(f"background: {t.BORDER_SOFT}; border: none;")
    return line
