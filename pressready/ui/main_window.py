"""
Main application window — dark theme, two-column layout.
Left column: toolbar + sheet canvas.   Right column: icon tab bar + settings.
"""

import math
import os
import sys
import webbrowser
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStatusBar, QFileDialog, QTabBar, QStackedWidget,
    QProgressDialog, QMessageBox, QFrame, QDialog, QScrollArea,
    QTextBrowser, QDialogButtonBox, QToolButton, QButtonGroup,
    QSizePolicy, QApplication,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings, QRectF, QPointF, QSize
from PyQt6.QtGui import (
    QFont, QDragEnterEvent, QDropEvent, QAction, QKeySequence,
    QIcon, QPixmap, QPainter, QPen, QColor, QPolygonF,
)

from pressready import __version__
from pressready.engine.data_model import Project, LayoutType
from pressready.engine.impose import impose
from pressready.ui.preprocessors_tab import PreprocessorsTab
from pressready.ui.layout_tab import LayoutTab
from pressready.ui.sheet_tab import SheetTab
from pressready.ui.marks_tab import MarksTab
from pressready.ui.preview_panel import SheetCanvas

_APP_TITLE = "PressReady v2"
_MAX_RECENT = 8
_ICON_SZ = 22
_TAB_SZ = 24
_TAB_NAMES = ["Preprocessors", "Layout", "Sheet", "Marks"]

# ── dark palette ─────────────────────────────────────

_ACCENT = "#D07B24"
_ACCENT_HOVER = "#BC6F20"
_ACCENT_PRESS = "#A8631C"

_BG = "#1e1e1e"
_BG2 = "#252526"
_BG3 = "#2d2d2d"
_BG_INPUT = "#3c3c3c"
_BORDER = "#3e3e42"
_TEXT = "#d4d4d4"
_TEXT_DIM = "#888"

_CLR = QColor(185, 185, 190)
_FILL = QColor(75, 78, 85)

_TOOL_BTN_STYLE = (
    "QToolButton { padding: 4px; border-radius: 3px; border: none;"
    "              background: transparent; }"
    "QToolButton:hover { background: rgba(255,255,255,0.08); }"
    "QToolButton:checked { background: rgba(255,255,255,0.14);"
    "                      border: 1px solid #666; }"
)


# ── global dark stylesheet ───────────────────────────

_DARK_STYLE = f"""
/* base */
QWidget {{ color: {_TEXT}; }}
QMainWindow {{ background: {_BG}; }}
QDialog {{ background: {_BG}; }}

/* menu */
QMenuBar {{ background: {_BG3}; color: #ccc; border-bottom: 1px solid {_BORDER}; padding: 2px 0; }}
QMenuBar::item {{ padding: 4px 10px; background: transparent; }}
QMenuBar::item:selected {{ background: {_BORDER}; }}
QMenu {{ background: #2d2d30; color: #ccc; border: 1px solid #454545; padding: 4px 0; }}
QMenu::item {{ padding: 5px 28px 5px 20px; }}
QMenu::item:selected {{ background: {_ACCENT}; color: #fff; }}
QMenu::separator {{ height: 1px; background: {_BORDER}; margin: 4px 8px; }}
QMenu::item:disabled {{ color: #666; }}

/* status */
QStatusBar {{ background: {_BG}; color: {_TEXT_DIM}; border-top: 1px solid {_BORDER}; }}

/* labels */
QLabel {{ background: transparent; }}

/* inputs */
QComboBox {{ background: {_BG_INPUT}; color: {_TEXT}; border: 1px solid #555;
             padding: 4px 8px; border-radius: 3px; min-height: 18px; }}
QComboBox:hover, QComboBox:focus {{ border-color: {_ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{ background: #2d2d30; color: {_TEXT};
    selection-background-color: {_ACCENT}; selection-color: #fff;
    border: 1px solid #555; outline: none; }}

QSpinBox, QDoubleSpinBox {{ background: {_BG_INPUT}; color: {_TEXT};
    border: 1px solid #555; padding: 3px 6px; border-radius: 3px; }}
QSpinBox:hover, QDoubleSpinBox:hover {{ border-color: {_ACCENT}; }}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background: #4a4a4a; border: none; width: 16px; }}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background: #5a5a5a; }}

QLineEdit {{ background: {_BG_INPUT}; color: {_TEXT};
    border: 1px solid #555; padding: 4px 6px; border-radius: 3px; }}
QLineEdit:focus {{ border-color: {_ACCENT}; }}

/* buttons */
QPushButton {{ background: {_BG_INPUT}; color: {_TEXT};
    border: 1px solid #555; padding: 5px 14px; border-radius: 3px; }}
QPushButton:hover {{ background: #4a4a4a; border-color: #666; }}
QPushButton:pressed {{ background: #333; }}
QPushButton:disabled {{ color: #666; background: #2a2a2a; border-color: #444; }}

/* checkbox / radio */
QCheckBox, QRadioButton {{ spacing: 6px; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px; height: 16px; border: 1px solid #555; background: {_BG_INPUT}; }}
QCheckBox::indicator {{ border-radius: 3px; }}
QRadioButton::indicator {{ border-radius: 8px; }}
QCheckBox::indicator:checked {{ background: {_ACCENT}; border-color: {_ACCENT}; }}
QRadioButton::indicator:checked {{ background: {_ACCENT}; border-color: {_ACCENT}; }}

/* group box */
QGroupBox {{ border: 1px solid {_BORDER}; border-radius: 4px;
    margin-top: 10px; padding-top: 14px; font-weight: bold; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px;
    padding: 0 5px; color: {_ACCENT}; }}

/* list */
QListWidget, QListView {{ background: #2d2d30; color: {_TEXT};
    border: 1px solid {_BORDER}; border-radius: 3px; outline: none; }}
QListWidget::item {{ padding: 4px 8px; }}
QListWidget::item:selected {{ background: {_ACCENT}; color: #fff; }}
QListWidget::item:hover:!selected {{ background: {_BORDER}; }}

/* scrollbar */
QScrollBar:vertical {{ background: {_BG2}; width: 10px; border: none; }}
QScrollBar::handle:vertical {{ background: #555; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #777; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QScrollBar:horizontal {{ background: {_BG2}; height: 10px; border: none; }}
QScrollBar::handle:horizontal {{ background: #555; border-radius: 5px; min-width: 30px; }}
QScrollBar::handle:horizontal:hover {{ background: #777; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}

/* misc */
QToolTip {{ background: #2d2d30; color: {_TEXT}; border: 1px solid #555; padding: 4px 8px; }}
QTextBrowser {{ background: {_BG}; color: {_TEXT}; border: 1px solid {_BORDER}; }}
QProgressBar {{ background: {_BG_INPUT}; border: 1px solid #555;
    border-radius: 3px; text-align: center; color: {_TEXT}; }}
QProgressBar::chunk {{ background: {_ACCENT}; border-radius: 3px; }}
QScrollArea {{ border: none; background: transparent; }}
QTabWidget::pane {{ border: 1px solid {_BORDER}; background: {_BG2}; }}
QSplitter::handle {{ background: {_BORDER}; }}
"""


# ── icon factory ─────────────────────────────────────


def _icon(draw_fn, size=_ICON_SZ) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    draw_fn(p)
    p.end()
    return QIcon(pm)


# -- toolbar icons

def _ico_1col():
    def draw(p):
        p.setPen(QPen(_CLR, 1.3))
        p.setBrush(_FILL)
        p.drawRect(QRectF(6, 2, 10, 18))
    return _icon(draw)


def _ico_2col():
    def draw(p):
        p.setPen(QPen(_CLR, 1.2))
        p.setBrush(_FILL)
        p.drawRect(QRectF(1, 3, 8.5, 16))
        p.drawRect(QRectF(12.5, 3, 8.5, 16))
    return _icon(draw)


def _ico_4col():
    def draw(p):
        p.setPen(QPen(_CLR, 1.0))
        p.setBrush(_FILL)
        for i in range(4):
            p.drawRect(QRectF(1 + i * 5.3, 4, 4, 14))
    return _icon(draw)


def _ico_zoom_in():
    def draw(p):
        p.setPen(QPen(_CLR, 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(9, 9), 5.5, 5.5)
        p.drawLine(QPointF(13, 13), QPointF(18, 18))
        p.drawLine(QPointF(7, 9), QPointF(11, 9))
        p.drawLine(QPointF(9, 7), QPointF(9, 11))
    return _icon(draw)


def _ico_zoom_out():
    def draw(p):
        p.setPen(QPen(_CLR, 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(9, 9), 5.5, 5.5)
        p.drawLine(QPointF(13, 13), QPointF(18, 18))
        p.drawLine(QPointF(7, 9), QPointF(11, 9))
    return _icon(draw)


def _ico_fit_width():
    def draw(p):
        p.setPen(QPen(_CLR, 1.3))
        p.drawLine(QPointF(2, 11), QPointF(20, 11))
        p.drawLine(QPointF(2, 11), QPointF(6, 8))
        p.drawLine(QPointF(2, 11), QPointF(6, 14))
        p.drawLine(QPointF(20, 11), QPointF(16, 8))
        p.drawLine(QPointF(20, 11), QPointF(16, 14))
    return _icon(draw)


def _ico_fit_page():
    def draw(p):
        p.setPen(QPen(_CLR, 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(4, 3, 14, 16))
        p.drawLine(QPointF(8, 11), QPointF(14, 11))
        p.drawLine(QPointF(11, 8), QPointF(11, 14))
    return _icon(draw)


def _ico_actual():
    def draw(p):
        f = QFont("Segoe UI", 8)
        f.setBold(True)
        p.setFont(f)
        p.setPen(_CLR)
        p.drawText(QRectF(0, 0, _ICON_SZ, _ICON_SZ),
                    Qt.AlignmentFlag.AlignCenter, "1:1")
    return _icon(draw)


# -- settings-panel tab icons

def _ico_tab_preproc():
    def draw(p):
        p.setPen(QPen(_CLR, 1.2))
        p.setBrush(QColor(55, 58, 65))
        p.drawRect(QRectF(8, 1, 12, 15))
        p.setBrush(_FILL)
        p.drawRect(QRectF(3, 5, 12, 15))
    return _icon(draw, _TAB_SZ)


def _ico_tab_layout():
    def draw(p):
        p.setPen(QPen(_CLR, 1.2))
        p.setBrush(_FILL)
        g = 2.0
        w = (_TAB_SZ - g * 3) / 2
        for r in range(2):
            for c in range(2):
                p.drawRect(QRectF(g + c * (w + g), g + r * (w + g), w, w))
    return _icon(draw, _TAB_SZ)


def _ico_tab_sheet():
    def draw(p):
        p.setPen(QPen(_CLR, 1.2))
        p.setBrush(_FILL)
        p.drawRect(QRectF(4, 1, 16, 22))
        p.setPen(QPen(QColor(120, 120, 125), 0.8))
        for y in (7, 11, 15):
            p.drawLine(QPointF(7, y), QPointF(17, y))
    return _icon(draw, _TAB_SZ)


def _ico_tab_marks():
    def draw(p):
        c = _TAB_SZ / 2.0
        p.setPen(QPen(_CLR, 1.0))
        p.setBrush(QColor(85, 90, 100))
        pts = []
        for i in range(12):
            a = i * math.pi / 6
            r = 9.5 if i % 2 == 0 else 6.0
            pts.append(QPointF(c + r * math.cos(a), c + r * math.sin(a)))
        p.drawPolygon(QPolygonF(pts))
        p.setBrush(QColor(50, 52, 58))
        p.drawEllipse(QPointF(c, c), 3, 3)
    return _icon(draw, _TAB_SZ)


# ── helpers ──────────────────────────────────────────


def _make_tool_btn(icon, tooltip, checkable=False, checked=False):
    btn = QToolButton()
    btn.setIcon(icon)
    btn.setToolTip(tooltip)
    btn.setCheckable(checkable)
    btn.setChecked(checked)
    btn.setIconSize(QSize(_ICON_SZ, _ICON_SZ))
    btn.setStyleSheet(_TOOL_BTN_STYLE)
    return btn


def _vsep(h=22):
    f = QFrame()
    f.setFixedSize(1, h)
    f.setStyleSheet(f"background: #555;")
    return f


def _scrollable(widget):
    sa = QScrollArea()
    sa.setWidget(widget)
    sa.setWidgetResizable(True)
    sa.setFrameShape(QFrame.Shape.NoFrame)
    sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    return sa


# ── export worker ────────────────────────────────────


class _ExportWorker(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(int, str)
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project: Optional[Project] = None
        self._output: str = ""

    def setup(self, project: Project, output_path: str):
        self._project = project
        self._output = output_path

    def run(self):
        try:
            def cb(cur, tot):
                self.progress.emit(cur, tot)
            n = impose(self._project, self._output, progress_callback=cb)
            self.finished.emit(n, self._output)
        except Exception as e:
            self.error.emit(str(e))


# ── dialogs ──────────────────────────────────────────


class _TutorialsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PressReady \u2014 Tutorials & Documentation")
        self.resize(720, 600)
        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(_TUTORIALS_HTML)
        layout.addWidget(browser)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(self.close)
        layout.addWidget(btns)


class _SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(400, 250)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Application settings will be available here in a future update.\n\n"
            "Planned:\n"
            "  \u2022 Default sheet size & margins\n"
            "  \u2022 Preview quality (DPI)\n"
            "  \u2022 Default marks to add\n"
            "  \u2022 Export options (compression, garbage collection)"
        ))
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(self.close)
        layout.addWidget(btns)


# ── main window ──────────────────────────────────────


def app_icon() -> QIcon:
    import sys, pathlib
    if getattr(sys, "frozen", False):
        base = pathlib.Path(sys._MEIPASS) / "assets" / "icons"
    else:
        base = pathlib.Path(__file__).resolve().parent.parent.parent / "assets" / "icons"
    icon = QIcon()
    for sz in (16, 24, 32, 48, 64, 128, 256):
        p = base / f"icon_{sz}x{sz}.png"
        if p.exists():
            icon.addPixmap(QPixmap(str(p)))
    return icon


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(_DARK_STYLE)
        self.setWindowIcon(app_icon())
        self._update_title()
        self.setMinimumSize(1100, 750)
        self.resize(1440, 900)
        self.setAcceptDrops(True)

        self._project = Project()
        self._recent_files: list[str] = []
        self._progress_dlg: Optional[QProgressDialog] = None
        self._settings = QSettings("PressReady", "PressReady2")

        self._export_worker = _ExportWorker(self)
        self._export_worker.progress.connect(self._on_export_progress)
        self._export_worker.finished.connect(self._on_export_done)
        self._export_worker.error.connect(self._on_export_err)

        self._load_recent_files()
        self._build_menubar()
        self._build_main_area()
        self._connect_signals()

    # ── title ────────────────────────────────────

    def _update_title(self, filename: str = ""):
        if filename:
            self.setWindowTitle(f"{_APP_TITLE} \u2014 {filename}")
        else:
            self.setWindowTitle(f"{_APP_TITLE} \u2014 PDF Imposition Tool")

    # ── menu bar ─────────────────────────────────

    def _build_menubar(self):
        mb = self.menuBar()

        # File
        fm = mb.addMenu("&File")
        self._act_open = QAction("&Open PDF\u2026", self)
        self._act_open.setShortcut(QKeySequence("Ctrl+O"))
        self._act_open.triggered.connect(self._on_open)
        fm.addAction(self._act_open)

        self._recent_menu = fm.addMenu("Open &Recent")
        self._rebuild_recent_menu()

        self._act_close = QAction("&Close PDF", self)
        self._act_close.setShortcut(QKeySequence("Ctrl+F4"))
        self._act_close.setEnabled(False)
        self._act_close.triggered.connect(self._on_close_pdf)
        fm.addAction(self._act_close)

        fm.addSeparator()
        self._act_generate = QAction("&Generate PDF", self)
        self._act_generate.setShortcut(QKeySequence("Ctrl+G"))
        self._act_generate.setEnabled(False)
        self._act_generate.triggered.connect(self._on_export)
        fm.addAction(self._act_generate)

        fm.addSeparator()
        fm.addAction(QAction("&Settings\u2026", self, triggered=self._on_settings))
        fm.addSeparator()
        fm.addAction(QAction("&Quit PressReady", self,
                             shortcut=QKeySequence("Alt+F4"), triggered=self.close))

        # Edit
        em = mb.addMenu("&Edit")
        em.addAction(QAction("&Undo", self, shortcut="Ctrl+Z", enabled=False))
        em.addAction(QAction("&Redo", self, shortcut="Ctrl+Y", enabled=False))
        em.addSeparator()
        em.addAction(QAction("Select &All", self, shortcut="Ctrl+A", enabled=False))

        # View
        vm = mb.addMenu("&View")
        vm.addAction(QAction("Zoom &In", self, shortcut="Ctrl++",
                              triggered=lambda: self._canvas.zoom_in()))
        vm.addAction(QAction("Zoom &Out", self, shortcut="Ctrl+-",
                              triggered=lambda: self._canvas.zoom_out()))
        vm.addAction(QAction("&Reset Zoom", self, shortcut="Ctrl+0",
                              triggered=lambda: self._canvas.fit_width()))
        vm.addSeparator()

        self._act_nums = QAction("Show Page &Numbers", self, checkable=True,
                                  checked=True, shortcut="Alt+1")
        self._act_nums.toggled.connect(self._on_view_toggle)
        vm.addAction(self._act_nums)

        self._act_frames = QAction("Show Page &Frames", self, checkable=True,
                                    checked=True, shortcut="Alt+2")
        self._act_frames.toggled.connect(self._on_view_toggle)
        vm.addAction(self._act_frames)

        self._act_tops = QAction("Show Page &Tops", self, checkable=True,
                                  checked=False, shortcut="Alt+3")
        self._act_tops.toggled.connect(self._on_view_toggle)
        vm.addAction(self._act_tops)

        self._act_previews = QAction("Show Page Pre&views", self, checkable=True,
                                      checked=True, shortcut="Alt+4")
        self._act_previews.toggled.connect(self._on_view_toggle)
        vm.addAction(self._act_previews)

        # Help
        hm = mb.addMenu("&Help")
        hm.addAction(QAction("&Tutorials", self, shortcut="F1",
                              triggered=self._on_tutorials))
        hm.addSeparator()
        hm.addAction(QAction("Open &System Folder", self, triggered=self._on_sysdir))
        hm.addSeparator()
        hm.addAction(QAction("&About\u2026", self, triggered=self._on_about))

    # ── main area (two-column layout) ────────────

    def _build_main_area(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ─── left column: toolbar + canvas ───
        left = QWidget()
        left_v = QVBoxLayout(left)
        left_v.setContentsMargins(0, 0, 0, 0)
        left_v.setSpacing(0)

        left_v.addWidget(self._create_toolbar())

        self._canvas = SheetCanvas()
        left_v.addWidget(self._canvas, 1)

        root.addWidget(left, 1)

        # ─── right column: icon tabs + content ───
        root.addWidget(self._create_settings_panel())

        # ─── status bar ───
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready \u2014 open a PDF to get started")

    # ── toolbar (left column only) ───────────────

    def _create_toolbar(self):
        bar = QFrame()
        bar.setFixedHeight(38)
        bar.setObjectName("tb")
        bar.setStyleSheet(
            f"#tb {{ background: {_BG3}; border-bottom: 1px solid {_BORDER}; }}"
        )

        h = QHBoxLayout(bar)
        h.setContentsMargins(8, 3, 8, 3)
        h.setSpacing(3)

        # column layout (exclusive toggle group) — stays left
        col_grp = QButtonGroup(self)
        col_grp.setExclusive(True)

        btn1 = _make_tool_btn(_ico_1col(), "Single column view", checkable=True)
        btn2 = _make_tool_btn(_ico_2col(), "Two column view", checkable=True, checked=True)
        btn4 = _make_tool_btn(_ico_4col(), "Four column view", checkable=True)

        col_grp.addButton(btn1, 1)
        col_grp.addButton(btn2, 2)
        col_grp.addButton(btn4, 4)
        col_grp.idClicked.connect(lambda n: self._canvas.set_columns(n))

        h.addWidget(btn1)
        h.addWidget(btn2)
        h.addWidget(btn4)

        # ── centered group: zoom + fit ──
        h.addStretch(1)

        zi = _make_tool_btn(_ico_zoom_in(), "Zoom in")
        zi.clicked.connect(lambda: self._canvas.zoom_in())
        h.addWidget(zi)

        zo = _make_tool_btn(_ico_zoom_out(), "Zoom out")
        zo.clicked.connect(lambda: self._canvas.zoom_out())
        h.addWidget(zo)

        h.addWidget(_vsep())

        fw = _make_tool_btn(_ico_fit_width(), "Fit to width")
        fw.clicked.connect(lambda: self._canvas.fit_width())
        h.addWidget(fw)

        fp = _make_tool_btn(_ico_fit_page(), "Fit to page")
        fp.clicked.connect(lambda: self._canvas.fit_page())
        h.addWidget(fp)

        ac = _make_tool_btn(_ico_actual(), "Actual size (1:1)")
        ac.clicked.connect(lambda: self._canvas.actual_size())
        h.addWidget(ac)

        h.addStretch(1)

        # Generate PDF — stays right
        self._gen_btn = QPushButton("  Generate PDF  ")
        self._gen_btn.setEnabled(False)
        self._gen_btn.setStyleSheet(
            f"QPushButton {{ background: {_ACCENT}; color: #fff; border: none;"
            f"              padding: 6px 18px; border-radius: 4px;"
            f"              font-weight: bold; font-size: 12px; }}"
            f"QPushButton:hover {{ background: {_ACCENT_HOVER}; }}"
            f"QPushButton:pressed {{ background: {_ACCENT_PRESS}; }}"
            f"QPushButton:disabled {{ background: #555; color: {_TEXT_DIM}; }}"
        )
        self._gen_btn.clicked.connect(self._on_export)
        h.addWidget(self._gen_btn)

        return bar

    # ── settings panel (right column) ────────────

    def _create_settings_panel(self):
        panel = QFrame()
        panel.setObjectName("sp")
        panel.setFixedWidth(310)
        panel.setStyleSheet(
            f"#sp {{ background: {_BG2}; border-left: 1px solid {_BORDER}; }}"
        )
        v = QVBoxLayout(panel)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # ─ icon tab bar ─
        self._tab_bar = QTabBar()
        self._tab_bar.setExpanding(True)
        self._tab_bar.setDrawBase(False)
        self._tab_bar.setIconSize(QSize(_TAB_SZ, _TAB_SZ))
        self._tab_bar.setStyleSheet(
            f"QTabBar {{ background: {_BG3}; }}"
            f"QTabBar::tab {{ padding: 9px 16px; border: none;"
            f"               border-bottom: 3px solid transparent; }}"
            f"QTabBar::tab:selected {{ border-bottom: 3px solid {_ACCENT};"
            f"                        background: #383838; }}"
            f"QTabBar::tab:hover:!selected {{ background: #353535; }}"
        )

        self._tab_bar.addTab(_ico_tab_preproc(), "")
        self._tab_bar.addTab(_ico_tab_layout(), "")
        self._tab_bar.addTab(_ico_tab_sheet(), "")
        self._tab_bar.addTab(_ico_tab_marks(), "")

        self._tab_bar.setTabToolTip(0, "Preprocessors")
        self._tab_bar.setTabToolTip(1, "Layout")
        self._tab_bar.setTabToolTip(2, "Sheet")
        self._tab_bar.setTabToolTip(3, "Marks")

        v.addWidget(self._tab_bar)

        # ─ active-tab heading ─
        self._tab_heading = QLabel(_TAB_NAMES[0])
        self._tab_heading.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {_TEXT};"
            f"padding: 10px 14px 6px 14px; background: {_BG2};"
        )
        v.addWidget(self._tab_heading)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {_BORDER};")
        v.addWidget(sep)

        # ─ stacked tab content ─
        self._stack = QStackedWidget()

        self._preproc_tab = PreprocessorsTab()
        self._layout_tab = LayoutTab()
        self._sheet_tab = SheetTab()
        self._marks_tab = MarksTab()

        self._stack.addWidget(_scrollable(self._preproc_tab))
        self._stack.addWidget(_scrollable(self._layout_tab))
        self._stack.addWidget(_scrollable(self._sheet_tab))
        self._stack.addWidget(_scrollable(self._marks_tab))

        v.addWidget(self._stack, 1)

        self._tab_bar.currentChanged.connect(self._on_tab_switch)

        return panel

    def _on_tab_switch(self, idx):
        self._stack.setCurrentIndex(idx)
        if 0 <= idx < len(_TAB_NAMES):
            self._tab_heading.setText(_TAB_NAMES[idx])

    # ── signal wiring ────────────────────────────

    def _connect_signals(self):
        self._preproc_tab.changed.connect(self._on_settings_changed)
        self._layout_tab.changed.connect(self._on_settings_changed)
        self._sheet_tab.changed.connect(self._on_settings_changed)
        self._marks_tab.changed.connect(self._on_settings_changed)

    # ── project assembly ─────────────────────────

    def build_project(self) -> Project:
        p = Project()
        p.source_pdf_path = self._project.source_pdf_path
        p.preprocessors = self._preproc_tab.get_steps()
        p.layout = self._layout_tab.get_settings()
        p.sheet = self._sheet_tab.get_settings()
        p.marks = self._marks_tab.get_marks()
        return p

    def _on_settings_changed(self):
        if not self._project.source_pdf_path:
            return
        project = self.build_project()
        self._canvas.update_project(project)

    def _on_view_toggle(self, _=None):
        self._canvas.set_overlays(
            show_tops=self._act_tops.isChecked(),
            show_numbers=self._act_nums.isChecked(),
            show_frames=self._act_frames.isChecked(),
            show_previews=self._act_previews.isChecked(),
        )

    # ── file operations ──────────────────────────

    def _on_open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF", "", "PDF Files (*.pdf);;All Files (*)")
        if path:
            self.load_pdf(path)

    def load_pdf(self, path: str):
        if not os.path.isfile(path):
            self._status.showMessage(f"File not found: {path}")
            return
        try:
            import fitz
            doc = fitz.open(path)
            count = len(doc)
            doc.close()
        except Exception as e:
            self._status.showMessage(f"Error: {e}")
            return

        self._project.source_pdf_path = path
        name = os.path.basename(path)
        self._update_title(name)
        self._status.showMessage(f"{name} \u2014 {count} pages")
        self._act_close.setEnabled(True)
        self._act_generate.setEnabled(True)
        self._gen_btn.setEnabled(True)

        self._add_recent(path)
        self._on_settings_changed()

    def _on_close_pdf(self):
        self._project.source_pdf_path = ""
        self._update_title()
        self._act_close.setEnabled(False)
        self._act_generate.setEnabled(False)
        self._gen_btn.setEnabled(False)
        self._canvas.clear_all()
        self._status.showMessage("PDF closed")

    def dragEnterEvent(self, ev: QDragEnterEvent):
        if ev.mimeData().hasUrls():
            u = ev.mimeData().urls()
            if u and u[0].toLocalFile().lower().endswith(".pdf"):
                ev.acceptProposedAction()
                return
        ev.ignore()

    def dropEvent(self, ev: QDropEvent):
        urls = ev.mimeData().urls()
        if urls:
            p = urls[0].toLocalFile()
            if p.lower().endswith(".pdf"):
                self.load_pdf(p)
                ev.acceptProposedAction()
                return
        ev.ignore()

    # ── recent files ─────────────────────────────

    def _load_recent_files(self):
        raw = self._settings.value("recent_files", [])
        self._recent_files = [f for f in (raw or []) if os.path.isfile(f)]

    def _save_recent_files(self):
        self._settings.setValue("recent_files", self._recent_files[:_MAX_RECENT])

    def _add_recent(self, path: str):
        path = os.path.normpath(path)
        if path in self._recent_files:
            self._recent_files.remove(path)
        self._recent_files.insert(0, path)
        self._recent_files = self._recent_files[:_MAX_RECENT]
        self._save_recent_files()
        self._rebuild_recent_menu()

    def _rebuild_recent_menu(self):
        self._recent_menu.clear()
        if not self._recent_files:
            a = self._recent_menu.addAction("(no recent files)")
            a.setEnabled(False)
            return
        for p in self._recent_files:
            a = self._recent_menu.addAction(os.path.basename(p))
            a.setData(p)
            a.triggered.connect(lambda _, fp=p: self.load_pdf(fp))
        self._recent_menu.addSeparator()
        self._recent_menu.addAction("Clear Recent", self._clear_recent)

    def _clear_recent(self):
        self._recent_files.clear()
        self._save_recent_files()
        self._rebuild_recent_menu()

    # ── export / generate ────────────────────────

    def _on_export(self):
        if not self._project.source_pdf_path:
            return
        project = self.build_project()
        base = os.path.splitext(os.path.basename(project.source_pdf_path))[0]
        lt = project.layout
        sfx = "booklet" if lt.layout_type == LayoutType.BOOKLET else f"{lt.nup}up"
        suggested = f"{base}_{sfx}_{project.sheet.preset}.pdf"

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Imposed PDF", suggested, "PDF Files (*.pdf)")
        if not path:
            return

        self._progress_dlg = QProgressDialog("Exporting\u2026", "Cancel", 0, 100, self)
        self._progress_dlg.setWindowTitle("Exporting")
        self._progress_dlg.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dlg.setMinimumDuration(0)
        self._gen_btn.setEnabled(False)
        self._export_worker.setup(project, path)
        self._export_worker.start()

    def _on_export_progress(self, cur, tot):
        try:
            if self._progress_dlg and not self._progress_dlg.wasCanceled():
                self._progress_dlg.setValue(int(cur / tot * 100) if tot else 0)
                self._progress_dlg.setLabelText(f"Sheet {cur + 1} / {tot}")
        except RuntimeError:
            pass

    def _on_export_done(self, n, path):
        try:
            if self._progress_dlg:
                self._progress_dlg.setValue(100)
                self._progress_dlg.close()
        except RuntimeError:
            pass
        self._progress_dlg = None
        self._gen_btn.setEnabled(True)
        self._status.showMessage(
            f"Exported {n} sheet(s) \u2192 {os.path.basename(path)}")
        QMessageBox.information(
            self, "Export Complete", f"Exported {n} sheet(s) to:\n{path}")

    def _on_export_err(self, msg):
        try:
            if self._progress_dlg:
                self._progress_dlg.close()
        except RuntimeError:
            pass
        self._progress_dlg = None
        self._gen_btn.setEnabled(True)
        self._status.showMessage(f"Export error: {msg}")
        QMessageBox.critical(self, "Export Error", f"Failed:\n{msg}")

    # ── menu actions ─────────────────────────────

    def _on_settings(self):
        _SettingsDialog(self).exec()

    def _on_tutorials(self):
        _TutorialsDialog(self).exec()

    def _on_sysdir(self):
        folder = os.path.dirname(os.path.abspath(sys.argv[0]))
        if sys.platform == "win32":
            os.startfile(folder)
        else:
            webbrowser.open(f"file://{folder}")

    def _on_about(self):
        QMessageBox.about(self, "About PressReady v2",
            f"<h2 style='color:{_ACCENT}'>PressReady v{__version__}</h2>"
            "<p>Professional PDF Imposition Tool</p>"
            "<p>Built with Python, PyQt6 &amp; PyMuPDF.</p>"
            "<hr><p><b>Features:</b> N-Up, Booklet, Preprocessors, "
            "Print Marks, WYSIWYG Preview, Vector Export.</p>"
            "<p>&copy; 2026 PressReady Team</p>")

    # ── cleanup ──────────────────────────────────

    def closeEvent(self, ev):
        self._canvas.cleanup()
        self._export_worker.wait()
        super().closeEvent(ev)


# ──────────────────────────────────────────────────────
#  Tutorials HTML — dark themed
# ──────────────────────────────────────────────────────

_TUTORIALS_HTML = f"""\
<html><head><style>
body{{font-family:'Segoe UI',sans-serif;padding:16px;color:#d4d4d4;background:#1e1e1e}}
h1{{color:{_ACCENT};border-bottom:2px solid {_ACCENT};padding-bottom:6px}}
h2{{color:{_ACCENT};margin-top:24px}}h3{{color:#aaa;margin-top:18px}}
code{{background:#3c3c3c;padding:2px 6px;border-radius:3px;font-size:13px;color:#ddd}}
table{{border-collapse:collapse;margin:8px 0;width:100%}}
td,th{{border:1px solid #3e3e42;padding:6px 10px;text-align:left}}
th{{background:#2d2d2d;color:{_ACCENT}}}
.tip{{background:#2a2a1a;border-left:4px solid {_ACCENT};padding:8px 12px;margin:10px 0}}
</style></head><body>
<h1>PressReady v2 &mdash; Tutorials &amp; Reference</h1>

<h2>1. Getting Started</h2>
<p>Use <b>File &rarr; Open PDF</b> (Ctrl+O) or <b>drag-and-drop</b> a PDF
onto the window. The preview canvas shows all imposed sheets.</p>
<p>Click <b style="color:{_ACCENT}">Generate PDF</b> (Ctrl+G) to export.</p>

<h2>2. Toolbar</h2>
<table>
<tr><th>Icon</th><th>Action</th></tr>
<tr><td>Single rect</td><td>1-column sheet view</td></tr>
<tr><td>Two rects</td><td>2-column sheet view (default)</td></tr>
<tr><td>Four rects</td><td>4-column sheet view</td></tr>
<tr><td>Magnifier +</td><td>Zoom in</td></tr>
<tr><td>Magnifier &minus;</td><td>Zoom out</td></tr>
<tr><td>&harr; arrows</td><td>Fit sheets to width</td></tr>
<tr><td>Rect +</td><td>Fit entire sheet in viewport</td></tr>
<tr><td>1:1</td><td>Actual size</td></tr>
</table>

<h2>3. Settings Panel Tabs</h2>
<p>The right panel uses icon tabs. Hover over each icon for its name,
or look at the heading that appears when you click a tab.</p>

<h2>4. Preprocessors Tab</h2>
<table>
<tr><th>Preprocessor</th><th>What it does</th></tr>
<tr><td><b>Rotate Pages</b></td><td>Rotates every page (90&deg;/180&deg;/270&deg;)</td></tr>
<tr><td><b>Scale Pages</b></td><td>Scales page size by a factor</td></tr>
<tr><td><b>Reorder Pages</b></td><td><code>reverse</code> or <code>4,3,2,1</code></td></tr>
</table>

<h2>5. Layout Tab</h2>
<p><b>N-Up:</b> 2 or 4 pages per sheet. <b>Booklet:</b> saddle-stitch reordering.</p>
<p><b>Gutters:</b> horizontal/vertical gaps (mm). <b>Page Range:</b> e.g. <code>1-4,7</code>.</p>
<p><b>Signatures:</b> multi-section booklets. <b>Page Creep:</b> compensate paper thickness.</p>

<h2>6. Sheet Tab</h2>
<p>Presets: A5&ndash;A2, Letter, Legal, Tabloid, Custom. Per-side margins. Landscape/Portrait.</p>

<h2>7. Marks Tab</h2>
<table>
<tr><th>Mark</th><th>Purpose</th></tr>
<tr><td>Crop Marks</td><td>Cut lines at page corners</td></tr>
<tr><td>Trim Line</td><td>Gray border around trim area</td></tr>
<tr><td>Registration</td><td>Crosshair targets for plate alignment</td></tr>
<tr><td>Folding Marks</td><td>Dashed fold indicators (booklet)</td></tr>
<tr><td>Text Label</td><td>Filename + sheet info in margin</td></tr>
<tr><td>Collating Marks</td><td>Spine marks for sheet order verification</td></tr>
</table>

<h2>8. View Overlays</h2>
<table>
<tr><th>Toggle</th><th>Shortcut</th><th>Description</th></tr>
<tr><td>Page Numbers</td><td>Alt+1</td><td>Magenta page numbers in each cell</td></tr>
<tr><td>Page Frames</td><td>Alt+2</td><td>Magenta border around cells</td></tr>
<tr><td>Page Tops</td><td>Alt+3</td><td>Magenta T-mark showing top edge</td></tr>
<tr><td>Page Previews</td><td>Alt+4</td><td>Show/hide actual PDF content</td></tr>
</table>

<h2>9. Keyboard Shortcuts</h2>
<table>
<tr><td>Ctrl+O</td><td>Open PDF</td></tr>
<tr><td>Ctrl+F4</td><td>Close PDF</td></tr>
<tr><td>Ctrl+G</td><td>Generate PDF</td></tr>
<tr><td>Ctrl++/&minus;</td><td>Zoom in/out</td></tr>
<tr><td>Ctrl+0</td><td>Fit to width</td></tr>
<tr><td>F1</td><td>Tutorials</td></tr>
<tr><td>Alt+F4</td><td>Quit</td></tr>
</table>
</body></html>
"""
