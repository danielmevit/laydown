"""Sheet tab — output sheet size, orientation, margins."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QComboBox, QDoubleSpinBox,
    QGroupBox, QLabel, QHBoxLayout,
)
from PyQt6.QtCore import pyqtSignal

from pressready.engine.data_model import SheetSettings, Orientation, SHEET_PRESETS_MM


class SheetTab(QWidget):
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._on_preset_changed()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # Size
        size_group = QGroupBox("Sheet Size")
        sl = QFormLayout(size_group)

        self._preset_combo = QComboBox()
        for name in SHEET_PRESETS_MM:
            w, h = SHEET_PRESETS_MM[name]
            self._preset_combo.addItem(f"{name}  ({w:.0f} × {h:.0f} mm)", name)
        self._preset_combo.addItem("Custom", "Custom")
        self._preset_combo.setCurrentIndex(2)  # A3
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        sl.addRow("Preset:", self._preset_combo)

        custom_w = QWidget()
        cwl = QHBoxLayout(custom_w)
        cwl.setContentsMargins(0, 0, 0, 0)
        self._cw_spin = QDoubleSpinBox()
        self._cw_spin.setRange(50, 2000)
        self._cw_spin.setValue(297)
        self._cw_spin.setSuffix(" mm")
        self._cw_spin.valueChanged.connect(self._emit)
        cwl.addWidget(self._cw_spin)
        cwl.addWidget(QLabel("×"))
        self._ch_spin = QDoubleSpinBox()
        self._ch_spin.setRange(50, 2000)
        self._ch_spin.setValue(420)
        self._ch_spin.setSuffix(" mm")
        self._ch_spin.valueChanged.connect(self._emit)
        cwl.addWidget(self._ch_spin)
        self._custom_widget = custom_w
        sl.addRow("", self._custom_widget)

        self._orient_combo = QComboBox()
        for o in Orientation:
            self._orient_combo.addItem(o.value, o)
        self._orient_combo.currentIndexChanged.connect(self._emit)
        sl.addRow("Orientation:", self._orient_combo)

        root.addWidget(size_group)

        # Margins
        margin_group = QGroupBox("Margins")
        ml = QFormLayout(margin_group)

        self._mt = self._make_margin_spin()
        ml.addRow("Top:", self._mt)
        self._mb = self._make_margin_spin()
        ml.addRow("Bottom:", self._mb)
        self._mleft = self._make_margin_spin()
        ml.addRow("Left:", self._mleft)
        self._mright = self._make_margin_spin()
        ml.addRow("Right:", self._mright)

        root.addWidget(margin_group)
        root.addStretch()

    def _make_margin_spin(self) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(0, 100)
        s.setValue(5.0)
        s.setSuffix(" mm")
        s.setSingleStep(1.0)
        s.valueChanged.connect(self._emit)
        return s

    def _on_preset_changed(self):
        is_custom = self._preset_combo.currentData() == "Custom"
        self._custom_widget.setVisible(is_custom)
        self._emit()

    # ── read / write ─────────────────────────────

    def get_settings(self) -> SheetSettings:
        s = SheetSettings()
        s.preset = self._preset_combo.currentData() or "A3"
        s.custom_width_mm = self._cw_spin.value()
        s.custom_height_mm = self._ch_spin.value()
        s.orientation = self._orient_combo.currentData() or Orientation.LANDSCAPE
        s.margin_top_mm = self._mt.value()
        s.margin_bottom_mm = self._mb.value()
        s.margin_left_mm = self._mleft.value()
        s.margin_right_mm = self._mright.value()
        return s

    def set_settings(self, s: SheetSettings):
        # preset
        for i in range(self._preset_combo.count()):
            if self._preset_combo.itemData(i) == s.preset:
                self._preset_combo.setCurrentIndex(i)
                break
        self._cw_spin.setValue(s.custom_width_mm)
        self._ch_spin.setValue(s.custom_height_mm)
        idx = [o for o in Orientation].index(s.orientation)
        self._orient_combo.setCurrentIndex(idx)
        self._mt.setValue(s.margin_top_mm)
        self._mb.setValue(s.margin_bottom_mm)
        self._mleft.setValue(s.margin_left_mm)
        self._mright.setValue(s.margin_right_mm)

    def _emit(self, *_):
        self.changed.emit()
