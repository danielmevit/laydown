"""Preprocessors tab — add/remove/configure page transforms."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QComboBox, QGroupBox, QFormLayout, QDoubleSpinBox,
    QLineEdit, QLabel, QStackedWidget, QCheckBox,
)
from PyQt6.QtCore import pyqtSignal, Qt

from pressready.engine.data_model import (
    PreprocessorStep, PreprocessorType, RotateAngle,
)


_AVAILABLE = [
    PreprocessorType.ROTATE_PAGES,
    PreprocessorType.SCALE_PAGES,
    PreprocessorType.REORDER_PAGES,
]


class PreprocessorsTab(QWidget):
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._steps: list[PreprocessorStep] = []
        self._setup_ui()

    # ── UI ───────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel("Page transforms applied before imposition.")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color:#888; font-size:11px; margin-bottom:6px;")
        root.addWidget(lbl)

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_select)
        root.addWidget(self._list)

        btn_row = QHBoxLayout()
        self._add_combo = QComboBox()
        for t in _AVAILABLE:
            self._add_combo.addItem(t.value, t)
        btn_row.addWidget(self._add_combo, stretch=1)

        add_btn = QPushButton("+")
        add_btn.setFixedWidth(32)
        add_btn.clicked.connect(self._on_add)
        btn_row.addWidget(add_btn)

        rm_btn = QPushButton("−")
        rm_btn.setFixedWidth(32)
        rm_btn.clicked.connect(self._on_remove)
        btn_row.addWidget(rm_btn)
        root.addLayout(btn_row)

        # Settings area (stacked for different types)
        self._settings_group = QGroupBox("Settings")
        settings_layout = QVBoxLayout(self._settings_group)

        self._stack = QStackedWidget()
        settings_layout.addWidget(self._stack)

        # 0 — empty
        self._stack.addWidget(QWidget())

        # 1 — Rotate
        rot_w = QWidget()
        rl = QFormLayout(rot_w)
        self._rotate_combo = QComboBox()
        for a in RotateAngle:
            self._rotate_combo.addItem(f"{a.value}°", a)
        self._rotate_combo.currentIndexChanged.connect(self._on_param_changed)
        rl.addRow("Angle:", self._rotate_combo)
        self._stack.addWidget(rot_w)

        # 2 — Scale
        sc_w = QWidget()
        sl = QFormLayout(sc_w)
        self._scale_spin = QDoubleSpinBox()
        self._scale_spin.setRange(0.1, 10.0)
        self._scale_spin.setValue(1.0)
        self._scale_spin.setSingleStep(0.1)
        self._scale_spin.setSuffix("×")
        self._scale_spin.valueChanged.connect(self._on_param_changed)
        sl.addRow("Factor:", self._scale_spin)
        self._stack.addWidget(sc_w)

        # 3 — Reorder
        ro_w = QWidget()
        ol = QFormLayout(ro_w)
        self._order_edit = QLineEdit()
        self._order_edit.setPlaceholderText("reverse  or  4,3,2,1")
        self._order_edit.textChanged.connect(self._on_param_changed)
        ol.addRow("Order:", self._order_edit)
        self._stack.addWidget(ro_w)

        root.addWidget(self._settings_group)
        root.addStretch()
        self._settings_group.setVisible(False)

    # ── public ───────────────────────────────────

    def get_steps(self) -> list[PreprocessorStep]:
        return list(self._steps)

    def set_steps(self, steps: list[PreprocessorStep]):
        self._steps = list(steps)
        self._rebuild_list()

    # ── internal ─────────────────────────────────

    def _rebuild_list(self):
        self._list.clear()
        for s in self._steps:
            prefix = "✓" if s.enabled else "✗"
            self._list.addItem(f"{prefix}  {s.type.value}")
        self._settings_group.setVisible(False)

    def _on_add(self):
        t = self._add_combo.currentData()
        step = PreprocessorStep(type=t)
        self._steps.append(step)
        self._rebuild_list()
        self._list.setCurrentRow(len(self._steps) - 1)
        self.changed.emit()

    def _on_remove(self):
        row = self._list.currentRow()
        if 0 <= row < len(self._steps):
            self._steps.pop(row)
            self._rebuild_list()
            self.changed.emit()

    def _on_select(self, row: int):
        if row < 0 or row >= len(self._steps):
            self._settings_group.setVisible(False)
            return
        step = self._steps[row]
        self._settings_group.setVisible(True)

        if step.type == PreprocessorType.ROTATE_PAGES:
            self._stack.setCurrentIndex(1)
            idx = [a for a in RotateAngle].index(step.rotate_angle)
            self._rotate_combo.blockSignals(True)
            self._rotate_combo.setCurrentIndex(idx)
            self._rotate_combo.blockSignals(False)
        elif step.type == PreprocessorType.SCALE_PAGES:
            self._stack.setCurrentIndex(2)
            self._scale_spin.blockSignals(True)
            self._scale_spin.setValue(step.scale_factor)
            self._scale_spin.blockSignals(False)
        elif step.type == PreprocessorType.REORDER_PAGES:
            self._stack.setCurrentIndex(3)
            self._order_edit.blockSignals(True)
            self._order_edit.setText(step.page_order)
            self._order_edit.blockSignals(False)
        else:
            self._stack.setCurrentIndex(0)

    def _on_param_changed(self):
        row = self._list.currentRow()
        if row < 0 or row >= len(self._steps):
            return
        step = self._steps[row]
        if step.type == PreprocessorType.ROTATE_PAGES:
            step.rotate_angle = self._rotate_combo.currentData()
        elif step.type == PreprocessorType.SCALE_PAGES:
            step.scale_factor = self._scale_spin.value()
        elif step.type == PreprocessorType.REORDER_PAGES:
            step.page_order = self._order_edit.text()
        self.changed.emit()
