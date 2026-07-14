"""Layout tab — choose imposition type and parameters."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QComboBox, QDoubleSpinBox,
    QSpinBox, QCheckBox, QGroupBox, QLabel, QLineEdit,
)
from PyQt6.QtCore import pyqtSignal

from pressready.engine.data_model import (
    LayoutSettings, LayoutType, BookletType, BookletMode, CreepMode,
)


class LayoutTab(QWidget):
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = LayoutSettings()
        self._setup_ui()
        self._on_type_changed()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # Layout type
        type_group = QGroupBox("Layout")
        tl = QFormLayout(type_group)

        self._type_combo = QComboBox()
        for lt in LayoutType:
            self._type_combo.addItem(lt.value, lt)
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        tl.addRow("Type:", self._type_combo)

        # N-Up count
        self._nup_combo = QComboBox()
        self._nup_combo.addItem("2-Up", 2)
        self._nup_combo.addItem("4-Up", 4)
        self._nup_combo.currentIndexChanged.connect(self._emit)
        tl.addRow("Pages/sheet:", self._nup_combo)

        # Booklet type
        self._booklet_type_combo = QComboBox()
        for bt in BookletType:
            self._booklet_type_combo.addItem(bt.value, bt)
        self._booklet_type_combo.currentIndexChanged.connect(self._emit)
        tl.addRow("Booklet type:", self._booklet_type_combo)

        # Mode
        self._mode_combo = QComboBox()
        for bm in BookletMode:
            self._mode_combo.addItem(bm.value, bm)
        self._mode_combo.currentIndexChanged.connect(self._emit)
        tl.addRow("Mode:", self._mode_combo)

        self._rtl_check = QCheckBox("Right to left")
        self._rtl_check.stateChanged.connect(self._emit)
        tl.addRow("", self._rtl_check)

        self._fillers_check = QCheckBox("Move fillers to the middle")
        self._fillers_check.stateChanged.connect(self._emit)
        tl.addRow("", self._fillers_check)

        root.addWidget(type_group)

        # Page range
        range_group = QGroupBox("Page Range")
        rl = QFormLayout(range_group)
        self._range_edit = QLineEdit()
        self._range_edit.setPlaceholderText("e.g. 1-4,7,10-12  (all if empty)")
        self._range_edit.textChanged.connect(self._emit)
        rl.addRow("Pages:", self._range_edit)
        root.addWidget(range_group)

        # Gutters
        gutter_group = QGroupBox("Gutters")
        gl = QFormLayout(gutter_group)

        self._gh_spin = QDoubleSpinBox()
        self._gh_spin.setRange(0, 100)
        self._gh_spin.setSuffix(" mm")
        self._gh_spin.valueChanged.connect(self._emit)
        gl.addRow("Horizontal:", self._gh_spin)

        self._gv_spin = QDoubleSpinBox()
        self._gv_spin.setRange(0, 100)
        self._gv_spin.setSuffix(" mm")
        self._gv_spin.valueChanged.connect(self._emit)
        gl.addRow("Vertical:", self._gv_spin)

        root.addWidget(gutter_group)

        # Signatures
        sig_group = QGroupBox("Signatures")
        sgl = QFormLayout(sig_group)

        self._sig_check = QCheckBox("Enable")
        self._sig_check.stateChanged.connect(self._emit)
        sgl.addRow(self._sig_check)

        self._sig_size_spin = QSpinBox()
        self._sig_size_spin.setRange(1, 100)
        self._sig_size_spin.setSuffix(" sheet(s)")
        self._sig_size_spin.valueChanged.connect(self._emit)
        sgl.addRow("Signature size:", self._sig_size_spin)

        root.addWidget(sig_group)

        # Page Creep
        creep_group = QGroupBox("Page Creep")
        cl = QFormLayout(creep_group)

        self._creep_check = QCheckBox("Enable")
        self._creep_check.stateChanged.connect(self._emit)
        cl.addRow(self._creep_check)

        self._creep_mode_combo = QComboBox()
        for cm in CreepMode:
            self._creep_mode_combo.addItem(cm.value, cm)
        self._creep_mode_combo.currentIndexChanged.connect(self._emit)
        cl.addRow("Mode:", self._creep_mode_combo)

        self._creep_outer = QDoubleSpinBox()
        self._creep_outer.setRange(0, 50)
        self._creep_outer.setSuffix(" mm")
        self._creep_outer.setDecimals(3)
        self._creep_outer.valueChanged.connect(self._emit)
        cl.addRow("Shift outer:", self._creep_outer)

        self._creep_inner = QDoubleSpinBox()
        self._creep_inner.setRange(0, 50)
        self._creep_inner.setSuffix(" mm")
        self._creep_inner.setDecimals(3)
        self._creep_inner.valueChanged.connect(self._emit)
        cl.addRow("Shift inner:", self._creep_inner)

        root.addWidget(creep_group)
        root.addStretch()

    # ── visibility logic ─────────────────────────

    def _on_type_changed(self):
        is_booklet = self._type_combo.currentData() == LayoutType.BOOKLET
        self._nup_combo.setVisible(not is_booklet)
        # find the label for nup_combo and toggle it too
        self._booklet_type_combo.setVisible(is_booklet)
        self._mode_combo.setVisible(is_booklet)
        self._rtl_check.setVisible(is_booklet)
        self._fillers_check.setVisible(is_booklet)
        self._emit()

    # ── read / write ─────────────────────────────

    def get_settings(self) -> LayoutSettings:
        s = LayoutSettings()
        s.layout_type = self._type_combo.currentData()
        s.nup = self._nup_combo.currentData() or 2
        s.booklet_type = self._booklet_type_combo.currentData() or BookletType.TWO_UP
        s.booklet_mode = self._mode_combo.currentData() or BookletMode.SHEETWISE
        s.right_to_left = self._rtl_check.isChecked()
        s.move_fillers_to_middle = self._fillers_check.isChecked()
        s.page_range = self._range_edit.text().strip()
        s.gutter_h_mm = self._gh_spin.value()
        s.gutter_v_mm = self._gv_spin.value()
        s.signatures_enabled = self._sig_check.isChecked()
        s.signature_size = self._sig_size_spin.value()
        s.creep_enabled = self._creep_check.isChecked()
        s.creep_mode = self._creep_mode_combo.currentData() or CreepMode.SHIFT_BOTH
        s.creep_outer_mm = self._creep_outer.value()
        s.creep_inner_mm = self._creep_inner.value()
        return s

    def set_settings(self, s: LayoutSettings):
        self._settings = s
        # populate widgets (block signals to avoid cascade)
        self._type_combo.blockSignals(True)
        idx = [lt for lt in LayoutType].index(s.layout_type)
        self._type_combo.setCurrentIndex(idx)
        self._type_combo.blockSignals(False)
        self._on_type_changed()

    def _emit(self, *_):
        self.changed.emit()
