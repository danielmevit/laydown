"""
The settings panel: schema in, widgets out.

Nothing here knows what a booklet or a bleed is. It walks ``ui/schema.SCHEMA``,
builds a control per entry, and writes every edit into one :class:`ValueStore`.
That single store is what makes undo/redo, per-section reset and presets fall out
almost for free, rather than each needing its own machinery.

Controls whose ``visible_when`` doesn't hold are *hidden*, not disabled — a control
that can't act must not be on screen (docs/ai/DECISIONS.md).
"""

import copy
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QSpinBox, QVBoxLayout, QWidget,
)

from pressready.engine.capabilities import assign
from pressready.engine.data_model import Project
from pressready.engine.utils import Unit
from pressready.ui import theme as t
from pressready.ui.components import (
    FieldRow, SectionHeader, Segmented, Switch, divider,
)
from pressready.ui.schema import (
    SCHEMA, Control, ControlType, Section, Tab, all_controls, defaults, is_length,
    is_visible,
)

_UNDO_LIMIT = 200


class LengthSpin(QDoubleSpinBox):
    """
    A length field: stores millimetres, shows whatever unit the operator prefers.

    The model is millimetres throughout (docs/ai/DECISIONS.md), so the unit never
    reaches the engine — it only changes what gets typed and read. A US shop setting
    up Letter work can think in inches without anyone converting by hand.
    """

    mm_changed = pyqtSignal(float)

    def __init__(self, minimum_mm: float, maximum_mm: float, value_mm: float,
                 unit: Unit = Unit.MM, parent=None):
        super().__init__(parent)
        self._min_mm, self._max_mm = minimum_mm, maximum_mm
        self._mm = value_mm
        self._unit = unit
        self._syncing = False
        self.apply_unit(unit)
        self.valueChanged.connect(self._on_edited)

    def _on_edited(self, shown: float) -> None:
        if self._syncing:
            return
        self._mm = self._unit.to_mm(shown)
        self.mm_changed.emit(self._mm)

    def mm(self) -> float:
        return self._mm

    def set_mm(self, value: float) -> None:
        self._mm = value
        self._refresh()

    def apply_unit(self, unit: Unit) -> None:
        self._unit = unit
        self._refresh()

    def _refresh(self) -> None:
        self._syncing = True
        self.setDecimals(self._unit.decimals)
        self.setSingleStep(self._unit.step)
        self.setSuffix(self._unit.suffix)
        self.setRange(self._unit.from_mm(self._min_mm), self._unit.from_mm(self._max_mm))
        self.setValue(self._unit.from_mm(self._mm))
        self._syncing = False


class ValueStore(QObject):
    """
    Every setting the panel edits, in one place, keyed by schema target.

    One store is what lets undo be a snapshot rather than a per-widget protocol,
    and lets a preset be a dict rather than a migration.
    """

    changed = pyqtSignal()
    unit_changed = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._values: Dict[str, Any] = defaults()
        self._values["preprocessors"] = []
        self._values["marks"] = []
        self._undo: List[dict] = []
        self._redo: List[dict] = []
        self._batching = False
        # Display only — never reaches the engine, and so deliberately not a schema
        # target: the capability contract would rightly reject one.
        self._unit = Unit.MM

    @property
    def unit(self) -> Unit:
        return self._unit

    def set_unit(self, unit: Unit) -> None:
        if unit is self._unit:
            return
        self._unit = unit
        self.unit_changed.emit(unit)

    # -- read/write

    def get(self, target: str) -> Any:
        return self._values.get(target)

    def set(self, target: str, value: Any, *, record: bool = True) -> None:
        if self._values.get(target) == value:
            return
        if record:
            self._push_undo()
        self._values[target] = value
        if not self._batching:
            self.changed.emit()

    def values(self) -> dict:
        return copy.deepcopy(self._values)

    def load(self, values: dict, *, record: bool = True) -> None:
        if record:
            self._push_undo()
        self._values.update(copy.deepcopy(values))
        self.changed.emit()

    # -- history

    def _push_undo(self) -> None:
        self._undo.append(copy.deepcopy(self._values))
        del self._undo[:-_UNDO_LIMIT]
        self._redo.clear()

    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> None:
        if not self._undo:
            return
        self._redo.append(copy.deepcopy(self._values))
        self._values = self._undo.pop()
        self.changed.emit()

    def redo(self) -> None:
        if not self._redo:
            return
        self._undo.append(copy.deepcopy(self._values))
        self._values = self._redo.pop()
        self.changed.emit()

    # -- the product

    def to_project(self, source_pdf_path: str = "") -> Project:
        """Assemble a Project. Targets are dotted paths, so this is mechanical."""
        project = Project()
        for target, value in self._values.items():
            assign(project, target, copy.deepcopy(value))
        project.source_pdf_path = source_pdf_path
        return project

    def reset_targets(self, targets: List[str]) -> None:
        """Restore just these settings — what a section's Reset does."""
        self._push_undo()
        base = defaults()
        for target in targets:
            if target in base:
                self._values[target] = base[target]
        self.changed.emit()


def _build_control(control: Control, store: ValueStore) -> Optional[QWidget]:
    """One schema entry → one bound widget."""
    value = store.get(control.target)

    if control.type is ControlType.SWITCH:
        widget = Switch()
        widget.setChecked(bool(value))
        widget.toggled.connect(lambda v, c=control: store.set(c.target, bool(v)))
        row = QWidget()
        line = QHBoxLayout(row)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(t.SPACE_3)
        caption = QLabel(control.label)
        caption.setStyleSheet(f"color: {t.FG_MUTED}; font-size: {t.TEXT_XS}px;")
        caption.setWordWrap(True)
        if control.description:
            caption.setToolTip(control.description)
            widget.setToolTip(control.description)
        line.addWidget(caption, 1)
        line.addWidget(widget, 0, Qt.AlignmentFlag.AlignRight)
        row.setProperty("boundWidget", widget)
        return row

    if control.type is ControlType.SEGMENTED:
        widget = Segmented(list(control.options))
        widget.set_value(value)
        widget.changed.connect(lambda v, c=control: store.set(c.target, v))
        return FieldRow(control.label, widget, control.description)

    if control.type is ControlType.SELECT:
        widget = QComboBox()
        for option_value, text in control.options:
            widget.addItem(text, option_value)
        index = widget.findData(value)
        if index >= 0:
            widget.setCurrentIndex(index)
        widget.currentIndexChanged.connect(
            lambda _, c=control, w=widget: store.set(c.target, w.currentData()))
        return FieldRow(control.label, widget, control.description)

    if control.type is ControlType.NUMBER:
        if is_length(control):
            widget = LengthSpin(control.minimum, control.maximum, float(value or 0.0),
                                store.unit)
            widget.mm_changed.connect(lambda v, c=control: store.set(c.target, v))
        elif control.decimals:
            widget = QDoubleSpinBox()
            widget.setDecimals(control.decimals)
            widget.setRange(control.minimum, control.maximum)
            widget.setSingleStep(control.step)
            widget.setValue(value or 0)
            widget.valueChanged.connect(lambda v, c=control: store.set(c.target, v))
        else:
            widget = QSpinBox()
            widget.setRange(int(control.minimum), int(control.maximum))
            widget.setSingleStep(int(control.step) or 1)
            widget.setValue(int(value or 0))
            widget.valueChanged.connect(lambda v, c=control: store.set(c.target, v))
        if control.suffix and not is_length(control):
            widget.setSuffix(control.suffix)
        return FieldRow(control.label, widget, control.description)

    if control.type is ControlType.TEXT:
        widget = QLineEdit(str(value or ""))
        if control.placeholder:
            widget.setPlaceholderText(control.placeholder)
        widget.textChanged.connect(lambda v, c=control: store.set(c.target, v))
        return FieldRow(control.label, widget, control.description)

    return None  # collections are supplied by the caller


class SectionWidget(QWidget):
    """A titled, collapsible group of controls with its own reset."""

    def __init__(self, section: Section, store: ValueStore,
                 collection_factory=None, parent=None):
        super().__init__(parent)
        self.section = section
        self._store = store
        self._rows: List[tuple] = []

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)

        self.header = SectionHeader(section.title)
        self.header.reset_clicked.connect(self._reset)
        self.header.toggled.connect(self._set_expanded)
        column.addWidget(self.header)

        self._body = QWidget()
        body = QVBoxLayout(self._body)
        body.setContentsMargins(t.SPACE_3, t.SECTION_TOP_PAD, t.SPACE_3, t.SECTION_BOTTOM_PAD)
        body.setSpacing(t.SPACE_3)

        for control in section.controls:
            if control.type is ControlType.COLLECTION:
                widget = collection_factory(control) if collection_factory else None
            else:
                widget = _build_control(control, store)
            if widget is None:
                continue
            body.addWidget(widget)
            self._rows.append((control, widget))

        column.addWidget(self._body)
        column.addWidget(divider())
        store.unit_changed.connect(self.apply_unit)

    def apply_unit(self, unit) -> None:
        for _, widget in self._rows:
            field = getattr(widget, "widget", None)
            if isinstance(field, LengthSpin):
                field.apply_unit(unit)

    def sync_from_store(self, values: dict) -> None:
        """Push store values back into the widgets — after undo or a preset load."""
        for control, widget in self._rows:
            field = getattr(widget, "widget", None)
            if isinstance(field, LengthSpin):
                field.set_mm(float(values.get(control.target) or 0.0))

    def _set_expanded(self, expanded: bool) -> None:
        self._body.setVisible(expanded)

    def _reset(self) -> None:
        self._store.reset_targets([c.target for c in self.section.controls])

    def refresh(self, values: dict) -> bool:
        """Apply visibility; return whether this section has anything to show."""
        any_visible = False
        for control, widget in self._rows:
            visible = is_visible(control, values)
            widget.setVisible(visible)
            any_visible = any_visible or visible

        shown = any_visible and is_visible(self.section, values)
        self.setVisible(shown)  # a section with nothing usable hides itself
        return shown


class SchemaTab(QWidget):
    """One tab's worth of sections."""

    def __init__(self, tab: Tab, store: ValueStore, collection_factory=None, parent=None):
        super().__init__(parent)
        self.tab = tab
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)

        self.sections = [
            SectionWidget(section, store, collection_factory) for section in tab.sections
        ]
        for widget in self.sections:
            column.addWidget(widget)
        column.addStretch(1)

    def refresh(self, values: dict) -> None:
        for section in self.sections:
            section.refresh(values)

    def sync_from_store(self, values: dict) -> None:
        for section in self.sections:
            section.sync_from_store(values)
