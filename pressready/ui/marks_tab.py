"""Marks tab — add/remove print marks (crop, registration, folding, labels)."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QComboBox, QGroupBox, QFormLayout, QDoubleSpinBox, QSpinBox,
    QLabel, QStackedWidget, QLineEdit, QCheckBox,
)
from PyQt6.QtCore import pyqtSignal

from pressready.engine.data_model import MarkItem, MarkType


_AVAILABLE = list(MarkType)


class MarksTab(QWidget):
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[MarkItem] = []
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel("Print marks added to the output sheet.")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color:#888; font-size:11px; margin-bottom:6px;")
        root.addWidget(lbl)

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_select)
        root.addWidget(self._list)

        btn_row = QHBoxLayout()
        self._add_combo = QComboBox()
        for mt in _AVAILABLE:
            self._add_combo.addItem(mt.value, mt)
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

        # Settings stack
        self._settings_group = QGroupBox("Mark Settings")
        sgl = QVBoxLayout(self._settings_group)
        self._stack = QStackedWidget()
        sgl.addWidget(self._stack)

        # 0 — empty
        self._stack.addWidget(QWidget())

        # 1 — Crop Marks settings
        crop_w = QWidget()
        cl = QFormLayout(crop_w)
        self._crop_len = QDoubleSpinBox()
        self._crop_len.setRange(1, 30)
        self._crop_len.setValue(5.0)
        self._crop_len.setSuffix(" mm")
        self._crop_len.valueChanged.connect(self._on_param)
        cl.addRow("Length:", self._crop_len)

        self._crop_off = QDoubleSpinBox()
        self._crop_off.setRange(0, 20)
        self._crop_off.setValue(3.0)
        self._crop_off.setSuffix(" mm")
        self._crop_off.valueChanged.connect(self._on_param)
        cl.addRow("Offset:", self._crop_off)
        self._stack.addWidget(crop_w)

        # 2 — Text label settings
        txt_w = QWidget()
        tl = QFormLayout(txt_w)
        self._label_edit = QLineEdit()
        self._label_edit.setPlaceholderText("(auto: filename + sheet info)")
        self._label_edit.textChanged.connect(self._on_param)
        tl.addRow("Text:", self._label_edit)

        self._label_size = QSpinBox()
        self._label_size.setRange(4, 24)
        self._label_size.setValue(8)
        self._label_size.setSuffix(" pt")
        self._label_size.valueChanged.connect(self._on_param)
        tl.addRow("Font size:", self._label_size)
        self._stack.addWidget(txt_w)

        # 3 — Folding marks settings
        fold_w = QWidget()
        fl = QFormLayout(fold_w)
        self._fold_len = QDoubleSpinBox()
        self._fold_len.setRange(2, 50)
        self._fold_len.setValue(10.0)
        self._fold_len.setSuffix(" mm")
        self._fold_len.valueChanged.connect(self._on_param)
        fl.addRow("Line length:", self._fold_len)
        self._stack.addWidget(fold_w)

        # 4 — Custom mark: any PDF, stamped on the sheet
        custom_w = QWidget()
        xl = QFormLayout(custom_w)
        picker = QHBoxLayout()
        self._mark_path = QLineEdit()
        self._mark_path.setPlaceholderText("a PDF to stamp on the sheet")
        self._mark_path.textChanged.connect(self._on_param)
        picker.addWidget(self._mark_path, stretch=1)
        browse = QPushButton("…")
        browse.setFixedWidth(28)
        browse.clicked.connect(self._on_browse_mark)
        picker.addWidget(browse)
        xl.addRow("Artwork:", picker)

        self._mark_w = QDoubleSpinBox()
        self._mark_w.setRange(1, 500)
        self._mark_w.setValue(20.0)
        self._mark_w.setSuffix(" mm")
        self._mark_w.valueChanged.connect(self._on_param)
        xl.addRow("Width:", self._mark_w)

        self._mark_x = QDoubleSpinBox()
        self._mark_x.setRange(0, 5000)
        self._mark_x.setValue(10.0)
        self._mark_x.setSuffix(" mm")
        self._mark_x.valueChanged.connect(self._on_param)
        xl.addRow("From left:", self._mark_x)

        self._mark_y = QDoubleSpinBox()
        self._mark_y.setRange(0, 5000)
        self._mark_y.setValue(10.0)
        self._mark_y.setSuffix(" mm")
        self._mark_y.valueChanged.connect(self._on_param)
        xl.addRow("From top:", self._mark_y)
        self._stack.addWidget(custom_w)

        root.addWidget(self._settings_group)
        root.addStretch()

    def _on_browse_mark(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose mark artwork", "", "PDF Files (*.pdf)")
        if path:
            self._mark_path.setText(path)
        self._settings_group.setVisible(False)

    # ── public ───────────────────────────────────

    def get_marks(self) -> list[MarkItem]:
        return list(self._items)

    def set_marks(self, items: list[MarkItem]):
        self._items = list(items)
        self._rebuild()

    # ── internal ─────────────────────────────────

    def _rebuild(self):
        self._list.clear()
        for m in self._items:
            prefix = "✓" if m.enabled else "✗"
            self._list.addItem(f"{prefix}  {m.mark_type.value}")
        self._settings_group.setVisible(False)

    def _on_add(self):
        mt = self._add_combo.currentData()
        item = MarkItem(mark_type=mt)
        self._items.append(item)
        self._rebuild()
        self._list.setCurrentRow(len(self._items) - 1)
        self.changed.emit()

    def _on_remove(self):
        row = self._list.currentRow()
        if 0 <= row < len(self._items):
            self._items.pop(row)
            self._rebuild()
            self.changed.emit()

    def _on_select(self, row: int):
        if row < 0 or row >= len(self._items):
            self._settings_group.setVisible(False)
            return
        m = self._items[row]
        self._settings_group.setVisible(True)

        if m.mark_type in (MarkType.CROP_MARKS, MarkType.GAP_CROP_MARKS):
            self._stack.setCurrentIndex(1)
            self._crop_len.setEnabled(m.mark_type == MarkType.CROP_MARKS)
            self._crop_len.blockSignals(True)
            self._crop_len.setValue(m.crop_length_mm)
            self._crop_len.blockSignals(False)
            self._crop_off.blockSignals(True)
            self._crop_off.setValue(m.crop_offset_mm)
            self._crop_off.blockSignals(False)
        elif m.mark_type == MarkType.CUSTOM_MARK:
            self._stack.setCurrentIndex(4)
            for widget, value in ((self._mark_path, m.mark_pdf_path),
                                  (self._mark_w, m.mark_width_mm),
                                  (self._mark_x, m.mark_x_mm),
                                  (self._mark_y, m.mark_y_mm)):
                widget.blockSignals(True)
                widget.setText(value) if widget is self._mark_path else widget.setValue(value)
                widget.blockSignals(False)
        elif m.mark_type == MarkType.TEXT_LABEL:
            self._stack.setCurrentIndex(2)
            self._label_edit.blockSignals(True)
            self._label_edit.setText(m.label_text)
            self._label_edit.blockSignals(False)
            self._label_size.blockSignals(True)
            self._label_size.setValue(m.label_font_size)
            self._label_size.blockSignals(False)
        elif m.mark_type == MarkType.FOLDING_MARKS:
            self._stack.setCurrentIndex(3)
            self._fold_len.blockSignals(True)
            self._fold_len.setValue(m.fold_line_length_mm)
            self._fold_len.blockSignals(False)
        else:
            self._stack.setCurrentIndex(0)

    def _on_param(self, *_):
        row = self._list.currentRow()
        if row < 0 or row >= len(self._items):
            return
        m = self._items[row]
        if m.mark_type in (MarkType.CROP_MARKS, MarkType.GAP_CROP_MARKS):
            m.crop_length_mm = self._crop_len.value()
            m.crop_offset_mm = self._crop_off.value()
        elif m.mark_type == MarkType.CUSTOM_MARK:
            m.mark_pdf_path = self._mark_path.text()
            m.mark_width_mm = self._mark_w.value()
            m.mark_x_mm = self._mark_x.value()
            m.mark_y_mm = self._mark_y.value()
        elif m.mark_type == MarkType.TEXT_LABEL:
            m.label_text = self._label_edit.text()
            m.label_font_size = self._label_size.value()
        elif m.mark_type == MarkType.FOLDING_MARKS:
            m.fold_line_length_mm = self._fold_len.value()
        self.changed.emit()
