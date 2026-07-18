"""
Main application window — two columns: sheet canvas on the left, settings on the right.

The settings column is not built here. It is rendered from ``ui/schema.SCHEMA`` by
``ui/panel.py``, so adding a setting means adding a schema entry, and a control that
the engine doesn't honour fails the test suite rather than the operator's job.
"""

import os
import pathlib
import sys
import webbrowser
from typing import Optional

from PyQt6.QtCore import QSize, QSettings, Qt, QThread, pyqtSignal
from PyQt6.QtGui import (
    QAction, QActionGroup, QDragEnterEvent, QDropEvent, QIcon, QKeySequence, QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication, QButtonGroup, QDialog, QDialogButtonBox, QFileDialog, QFrame,
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QProgressDialog, QPushButton,
    QScrollArea, QStackedWidget, QStatusBar, QTabBar, QTextBrowser, QToolButton,
    QVBoxLayout, QWidget,
)

from laydown import __version__
from laydown.engine.data_model import LayoutType, Project
from laydown.engine.impose import impose
from laydown.engine.utils import Unit
from laydown.ui import theme as t
from laydown.ui.help import tutorials_html
from laydown.ui.icons import lucide
from laydown.ui.marks_tab import MarksTab
from laydown.ui.panel import SchemaTab, ValueStore
from laydown.ui.preprocessors_tab import PreprocessorsTab
from laydown.ui.preview_panel import SheetCanvas
from laydown.ui.schema import SCHEMA

_APP_TITLE = "Laydown"
_MAX_RECENT = 8
_ICON_SZ = 22
_TAB_SZ = 24

_TOOL_BTN_STYLE = (
    f"QToolButton {{ padding: 4px; border-radius: {t.RADIUS_SM}px; border: none;"
    f"               background: transparent; }}"
    f"QToolButton:hover {{ background: {t.HOVER_WASH}; }}"
    f"QToolButton:checked {{ background: {t.SELECTED_WASH}; }}"
)


# ── icons — the Lucide set (see laydown/ui/icons.py) ─

# Order matches the four settings tabs: Source, Layout, Sheet, Marks.
_TAB_ICON_NAMES = ("tab_source", "tab_layout", "tab_sheet", "tab_marks")


def _tool_btn(icon, tooltip, checkable=False, checked=False):
    b = QToolButton()
    b.setIcon(icon)
    b.setToolTip(tooltip)
    b.setCheckable(checkable)
    b.setChecked(checked)
    b.setIconSize(QSize(_ICON_SZ, _ICON_SZ))
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setStyleSheet(_TOOL_BTN_STYLE)
    return b


def _vsep(h=20):
    f = QFrame()
    f.setFixedSize(1, h)
    f.setStyleSheet(f"background: {t.BORDER};")
    return f


def app_icon() -> QIcon:
    if getattr(sys, "frozen", False):
        base = pathlib.Path(sys._MEIPASS) / "assets" / "icons"
    else:
        base = pathlib.Path(__file__).resolve().parent.parent.parent / "assets" / "icons"
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        p = base / f"icon_{size}x{size}.png"
        if p.exists():
            icon.addPixmap(QPixmap(str(p)))
    return icon


# ── export worker ────────────────────────────────────

class _ExportWorker(QThread):
    progress = pyqtSignal(int, int)
    done = pyqtSignal(int, str)
    failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project: Optional[Project] = None
        self._output = ""
        self._cancel = False

    def setup(self, project: Project, output_path: str):
        self._project = project
        self._output = output_path
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            def report(current, total):
                if self._cancel:
                    raise _Cancelled()
                self.progress.emit(current, total)
            self.done.emit(impose(self._project, self._output, progress_callback=report),
                           self._output)
        except _Cancelled:
            self.failed.emit("Export cancelled")
        except Exception as exc:
            self.failed.emit(str(exc))


class _Cancelled(Exception):
    """Raised inside the worker when the user cancels — the only way to stop mid-sheet."""


# ── dialogs ──────────────────────────────────────────

class _TutorialsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Laydown — Tutorials & Reference")
        self.resize(760, 640)
        column = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(tutorials_html())
        column.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.close)
        column.addWidget(buttons)


# ── main window ──────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Dress the whole application, not just this window: dialogs and any widget a
        # QSS rule doesn't reach need the dark palette too, or they fall back to the
        # platform's light one.
        app = QApplication.instance()
        if app is not None:
            t.apply(app)
        self.setWindowIcon(app_icon())
        self.setMinimumSize(1100, 750)
        self.resize(1440, 900)
        self.setAcceptDrops(True)

        self._source_path = ""
        self._source_doc = None   # kept open so preflight need not reopen it
        self._findings: list = []
        self._recent: list[str] = []
        self._progress: Optional[QProgressDialog] = None
        self._settings = QSettings("Laydown", "Laydown")

        self._store = ValueStore(self)
        self._store.changed.connect(self._on_values_changed)

        self._export = _ExportWorker(self)
        self._export.progress.connect(self._on_export_progress)
        self._export.done.connect(self._on_export_done)
        self._export.failed.connect(self._on_export_failed)

        self._update_title()
        self._load_recent()
        self._build_menubar()
        self._build_main_area()
        self._on_values_changed()

    # ── title ────────────────────────────────────

    def _update_title(self, filename: str = ""):
        suffix = filename or "PDF Imposition"
        self.setWindowTitle(f"{_APP_TITLE} — {suffix}")

    # ── menus ────────────────────────────────────

    def _build_menubar(self):
        bar = self.menuBar()

        def mi(name):  # a menu-sized Lucide icon
            return lucide(name, 16)

        file_menu = bar.addMenu("&File")
        self._act_open = QAction(mi("open"), "&Open PDF…", self,
                                 shortcut=QKeySequence("Ctrl+O"), triggered=self._on_open)
        file_menu.addAction(self._act_open)
        self._recent_menu = file_menu.addMenu("Open &Recent")
        self._recent_menu.setIcon(mi("recent"))
        self._rebuild_recent_menu()

        self._act_close = QAction(mi("close"), "&Close PDF", self,
                                  shortcut=QKeySequence("Ctrl+F4"),
                                  enabled=False, triggered=self._on_close_pdf)
        file_menu.addAction(self._act_close)
        file_menu.addSeparator()

        self._act_generate = QAction(mi("generate"), "&Generate PDF", self,
                                     shortcut=QKeySequence("Ctrl+G"),
                                     enabled=False, triggered=self._on_export)
        file_menu.addAction(self._act_generate)
        file_menu.addSeparator()
        file_menu.addAction(QAction(mi("save_preset"), "Save &Preset…", self,
                                    triggered=self._on_save_preset))
        file_menu.addAction(QAction(mi("load_preset"), "&Load Preset…", self,
                                    triggered=self._on_load_preset))
        file_menu.addSeparator()
        file_menu.addAction(QAction(mi("quit"), "&Quit", self,
                                    shortcut=QKeySequence("Alt+F4"), triggered=self.close))

        edit_menu = bar.addMenu("&Edit")
        self._act_undo = QAction(mi("undo"), "&Undo", self, shortcut="Ctrl+Z",
                                 enabled=False, triggered=self._undo)
        self._act_redo = QAction(mi("redo"), "&Redo", self, shortcut="Ctrl+Y",
                                 enabled=False, triggered=self._redo)
        edit_menu.addAction(self._act_undo)
        edit_menu.addAction(self._act_redo)
        edit_menu.addSeparator()
        edit_menu.addAction(QAction(mi("reset"), "Reset &All Settings", self,
                                    triggered=self._on_reset_all))

        view_menu = bar.addMenu("&View")
        view_menu.addAction(QAction(mi("zoom_in"), "Zoom &In", self, shortcut="Ctrl++",
                                    triggered=lambda: self._canvas.zoom_in()))
        view_menu.addAction(QAction(mi("zoom_out"), "Zoom &Out", self, shortcut="Ctrl+-",
                                    triggered=lambda: self._canvas.zoom_out()))
        view_menu.addAction(QAction(mi("fit_width"), "&Reset Zoom", self, shortcut="Ctrl+0",
                                    triggered=lambda: self._canvas.fit_width()))
        units_menu = view_menu.addMenu("&Units")
        units_menu.setIcon(mi("tab_sheet"))
        unit_group = QActionGroup(self)
        unit_group.setExclusive(True)
        for unit in Unit:
            action = QAction(f"{unit.name.title()} ({unit.value})", self, checkable=True,
                             checked=(unit is Unit.MM))
            action.triggered.connect(lambda _, u=unit: self._on_unit_changed(u))
            unit_group.addAction(action)
            units_menu.addAction(action)
        view_menu.addSeparator()

        self._act_nums = QAction("Show Page &Numbers", self, checkable=True, checked=True,
                                 shortcut="Alt+1")
        self._act_frames = QAction("Show Cut &Lines", self, checkable=True, checked=True,
                                   shortcut="Alt+2")
        self._act_tops = QAction("Show Page &Tops", self, checkable=True, checked=False,
                                 shortcut="Alt+3")
        self._act_previews = QAction("Show Page Pre&views", self, checkable=True, checked=True,
                                     shortcut="Alt+4")
        for action in (self._act_nums, self._act_frames, self._act_tops, self._act_previews):
            action.toggled.connect(self._on_view_toggle)
            view_menu.addAction(action)

        help_menu = bar.addMenu("&Help")
        help_menu.addAction(QAction(mi("tutorials"), "&Tutorials", self, shortcut="F1",
                                    triggered=self._on_tutorials))
        help_menu.addAction(QAction(mi("preflight"), "&Preflight…", self, shortcut="F7",
                                    triggered=self._show_preflight_details))
        help_menu.addSeparator()
        help_menu.addAction(QAction(mi("sysdir"), "Open &System Folder", self,
                                    triggered=self._on_sysdir))
        help_menu.addSeparator()
        help_menu.addAction(QAction(mi("about"), "&About…", self, triggered=self._on_about))

    # ── layout ───────────────────────────────────

    def _build_main_area(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        left = QWidget()
        column = QVBoxLayout(left)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(self._create_toolbar())
        column.addWidget(self._create_preflight_bar())
        self._canvas = SheetCanvas()
        self._canvas.open_requested.connect(self._on_open)  # double-click empty area
        column.addWidget(self._canvas, 1)
        root.addWidget(left, 1)

        root.addWidget(self._create_settings_panel())

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready — open a PDF to get started")

    def _create_toolbar(self):
        bar = QFrame()
        bar.setFixedHeight(40)
        bar.setObjectName("toolbar")
        bar.setStyleSheet(
            f"#toolbar {{ background: {t.RAISED}; border-bottom: 1px solid {t.BORDER}; }}")
        row = QHBoxLayout(bar)
        row.setContentsMargins(t.SPACE_3, t.SPACE_1, t.SPACE_3, t.SPACE_1)
        row.setSpacing(2)

        columns = QButtonGroup(self)
        columns.setExclusive(True)
        for count, glyph, tip in ((1, "columns_1", "Single column"),
                                  (2, "columns_2", "Two columns"),
                                  (4, "columns_4", "Four columns")):
            button = _tool_btn(lucide(glyph), tip, checkable=True, checked=(count == 2))
            columns.addButton(button, count)
            row.addWidget(button)
        columns.idClicked.connect(lambda n: self._canvas.set_columns(n))

        row.addStretch(1)
        for glyph, tip, slot in (
            ("zoom_in", "Zoom in", lambda: self._canvas.zoom_in()),
            ("zoom_out", "Zoom out", lambda: self._canvas.zoom_out()),
        ):
            button = _tool_btn(lucide(glyph), tip)
            button.clicked.connect(slot)
            row.addWidget(button)
        row.addWidget(_vsep())
        for glyph, tip, slot in (
            ("fit_width", "Fit to width", lambda: self._canvas.fit_width()),
            ("fit_page", "Fit whole sheet", lambda: self._canvas.fit_page()),
            ("actual_size", "Actual size (1:1)", lambda: self._canvas.actual_size()),
        ):
            button = _tool_btn(lucide(glyph), tip)
            button.clicked.connect(slot)
            row.addWidget(button)
        # No trailing stretch: the single stretch above pushes the whole zoom/fit
        # group to the right edge, with the column-view buttons kept at the left.
        return bar

    def _create_preflight_bar(self):
        """
        A strip that says what's wrong while there's still time to fix it.

        0.2.0 only reported trouble by raising at export — "margins too large" arrived
        after the operator hit Generate, and subtler problems arrived at the guillotine.
        """
        self._preflight_bar = QFrame()
        self._preflight_bar.setObjectName("preflight")
        self._preflight_bar.setVisible(False)
        row = QHBoxLayout(self._preflight_bar)
        row.setContentsMargins(t.SPACE_3, t.SPACE_2, t.SPACE_3, t.SPACE_2)
        row.setSpacing(t.SPACE_2)

        self._preflight_text = QLabel("")
        self._preflight_text.setWordWrap(True)
        row.addWidget(self._preflight_text, 1)

        self._preflight_more = QPushButton("Details")
        self._preflight_more.setCursor(Qt.CursorShape.PointingHandCursor)
        self._preflight_more.clicked.connect(self._show_preflight_details)
        row.addWidget(self._preflight_more, 0)
        return self._preflight_bar

    def _run_preflight(self):
        from laydown.engine.preflight import Severity, preflight

        self._findings = []
        if self._source_path:
            try:
                self._findings = preflight(self.build_project(), self._source_doc)
            except Exception:
                self._findings = []  # never let a check break the app it is checking

        # The strip is for things that need doing something about. Notes are true but
        # not urgent; they stay in Details (Help > Preflight) rather than sitting on
        # screen forever and teaching the operator to tune the strip out.
        loud = [f for f in self._findings
                if f.severity in (Severity.ERROR, Severity.WARNING)]
        notes = len(self._findings) - len(loud)
        if not loud:
            self._preflight_bar.setVisible(False)
            if notes and self._source_path:
                self._status.showMessage(
                    f"{notes} preflight note{'s' if notes > 1 else ''} — Help \u2192 Preflight")
            return

        worst = loud[0]
        colour = {Severity.ERROR: t.DESTRUCTIVE,
                  Severity.WARNING: t.ACCENT,
                  Severity.NOTE: t.FG_MUTED}[worst.severity]
        self._preflight_bar.setStyleSheet(
            f"#preflight {{ background: {t.RAISED}; border-bottom: 1px solid {colour}; }}")
        extra = len(self._findings) - 1
        suffix = f"   (+{extra} more)" if extra > 0 else ""
        self._preflight_text.setText(
            f"<span style='color:{colour}'><b>{worst.severity.value}</b></span> "
            f"<span style='color:{t.FG}'>{worst.message}</span>"
            f"<span style='color:{t.FG_FAINT}'>{suffix}</span>"
        )
        self._preflight_more.setVisible(bool(worst.detail) or extra > 0)
        self._preflight_bar.setVisible(True)

    def _show_preflight_details(self):
        if not getattr(self, "_findings", None):
            QMessageBox.information(self, "Preflight", "Nothing to report — this job looks fine.")
            return
        body = "".join(
            f"<p style='margin:0 0 10px 0'><b>{f.severity.value}:</b> {f.message}"
            + (f"<br><span style='color:{t.FG_MUTED}'>{f.detail}</span>" if f.detail else "")
            + "</p>"
            for f in self._findings
        )
        QMessageBox.information(self, "Preflight", f"<div>{body}</div>")

    def _collection_for(self, control):
        """Supply the bespoke editors for the two genuinely growable settings."""
        if control.target == "preprocessors":
            editor = PreprocessorsTab()
            editor.changed.connect(
                lambda: self._store.set("preprocessors", editor.get_steps()))
        elif control.target == "marks":
            editor = MarksTab()
            editor.changed.connect(lambda: self._store.set("marks", editor.get_marks()))
        else:
            return None
        self._collections[control.target] = editor
        return editor

    def _create_settings_panel(self):
        panel = QFrame()
        panel.setObjectName("settings")
        panel.setFixedWidth(t.PANEL_W)
        panel.setStyleSheet(
            f"#settings {{ background: {t.SURFACE}; border-left: 1px solid {t.BORDER}; }}")
        column = QVBoxLayout(panel)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)

        self._tab_bar = QTabBar()
        self._tab_bar.setExpanding(False)   # content-sized, so it can be centred as a group
        self._tab_bar.setDrawBase(False)
        self._tab_bar.setIconSize(QSize(_TAB_SZ, _TAB_SZ))
        self._tab_bar.setStyleSheet(
            f"QTabBar {{ background: transparent; }}"
            f"QTabBar::tab {{ padding: 9px 16px; border: none;"
            f"                border-bottom: 2px solid transparent; }}"
            f"QTabBar::tab:selected {{ border-bottom: 2px solid {t.ACCENT};"
            f"                         background: {t.SELECTED_WASH}; }}"
            f"QTabBar::tab:hover:!selected {{ background: {t.HOVER_WASH}; }}"
        )
        for index, tab in enumerate(SCHEMA):
            self._tab_bar.addTab(lucide(_TAB_ICON_NAMES[index], _TAB_SZ), "")
            self._tab_bar.setTabToolTip(index, tab.name)

        # Full-width header strip with the four tab icons centred in the middle.
        tab_header = QFrame()
        tab_header.setObjectName("tabheader")
        tab_header.setStyleSheet(f"#tabheader {{ background: {t.RAISED}; }}")
        header_row = QHBoxLayout(tab_header)
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(0)
        header_row.addStretch(1)
        header_row.addWidget(self._tab_bar)
        header_row.addStretch(1)
        column.addWidget(tab_header)

        self._heading = QLabel(SCHEMA[0].name)
        self._heading.setStyleSheet(
            f"font-size: {t.TEXT_LG}px; font-weight: 600; color: {t.FG};"
            f"padding: {t.SPACE_3}px {t.SPACE_3}px {t.SPACE_2}px {t.SPACE_3}px;"
        )
        column.addWidget(self._heading)

        self._collections: dict = {}
        self._stack = QStackedWidget()
        self._tabs = []
        for tab in SCHEMA:
            page = SchemaTab(tab, self._store, self._collection_for)
            self._tabs.append(page)
            area = QScrollArea()
            area.setWidget(page)
            area.setWidgetResizable(True)
            area.setFrameShape(QFrame.Shape.NoFrame)
            area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self._stack.addWidget(area)
        column.addWidget(self._stack, 1)
        self._tab_bar.currentChanged.connect(self._on_tab_switch)

        column.addWidget(self._create_footer())
        return panel

    def _create_footer(self):
        """
        Sticky footer for the one action that delivers the product.

        Toolcraft keeps final delivery actions pinned rather than in the toolbar, so
        the thing you came to do is always reachable without hunting.
        """
        footer = QFrame()
        footer.setObjectName("footer")
        footer.setStyleSheet(
            f"#footer {{ background: {t.RAISED}; border-top: 1px solid {t.BORDER}; }}")
        row = QVBoxLayout(footer)
        row.setContentsMargins(t.SPACE_3, t.SPACE_3, t.SPACE_3, t.SPACE_3)

        self._generate = QPushButton("  Generate PDF")
        self._generate.setIcon(lucide("generate", 18, t.ACCENT_FG))
        self._generate.setProperty("accent", True)
        self._generate.setEnabled(False)
        self._generate.setCursor(Qt.CursorShape.PointingHandCursor)
        self._generate.clicked.connect(self._on_export)
        row.addWidget(self._generate)
        return footer

    def _on_tab_switch(self, index):
        self._stack.setCurrentIndex(index)
        if 0 <= index < len(SCHEMA):
            self._heading.setText(SCHEMA[index].name)

    # ── the product ──────────────────────────────

    def build_project(self) -> Project:
        return self._store.to_project(self._source_path)

    def _on_values_changed(self):
        values = self._store.values()
        for tab in self._tabs:
            tab.refresh(values)
        self._act_undo.setEnabled(self._store.can_undo())
        self._act_redo.setEnabled(self._store.can_redo())
        self._run_preflight()
        if self._source_path:
            self._canvas.update_project(self.build_project())

    def _undo(self):
        self._store.undo()
        self._resync_widgets()
        self._rebuild_collection_editors()

    def _redo(self):
        self._store.redo()
        self._resync_widgets()
        self._rebuild_collection_editors()

    def _on_unit_changed(self, unit):
        self._store.set_unit(unit)
        self._settings.setValue("display_unit", unit.name)
        self._status.showMessage(f"Lengths shown in {unit.value}")

    def _on_view_toggle(self, _=None):
        self._canvas.set_overlays(
            show_tops=self._act_tops.isChecked(),
            show_numbers=self._act_nums.isChecked(),
            show_frames=self._act_frames.isChecked(),
            show_previews=self._act_previews.isChecked(),
        )

    # ── files ────────────────────────────────────

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
        except Exception as exc:
            self._status.showMessage(f"Could not open: {exc}")
            return

        self._close_source_doc()
        self._source_doc = doc
        self._source_path = path
        name = os.path.basename(path)
        self._update_title(name)
        self._status.showMessage(f"{name} — {count} page{'s' if count != 1 else ''}")
        for widget in (self._act_close, self._act_generate, self._generate):
            widget.setEnabled(True)
        self._add_recent(path)
        self._on_values_changed()

    def _close_source_doc(self):
        if self._source_doc is not None:
            try:
                self._source_doc.close()
            except Exception:
                pass
            self._source_doc = None

    def _on_close_pdf(self):
        self._close_source_doc()
        self._source_path = ""
        self._update_title()
        for widget in (self._act_close, self._act_generate, self._generate):
            widget.setEnabled(False)
        self._canvas.clear_all()
        self._run_preflight()
        self._status.showMessage("PDF closed")

    def dragEnterEvent(self, event: QDragEnterEvent):
        urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
        if urls and urls[0].toLocalFile().lower().endswith(".pdf"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls and urls[0].toLocalFile().lower().endswith(".pdf"):
            self.load_pdf(urls[0].toLocalFile())
            event.acceptProposedAction()
        else:
            event.ignore()

    # ── recent ───────────────────────────────────

    def _load_recent(self):
        raw = self._settings.value("recent_files", [])
        self._recent = [f for f in (raw or []) if os.path.isfile(f)]

    def _add_recent(self, path: str):
        path = os.path.normpath(path)
        if path in self._recent:
            self._recent.remove(path)
        self._recent.insert(0, path)
        del self._recent[_MAX_RECENT:]
        self._settings.setValue("recent_files", self._recent)
        self._rebuild_recent_menu()

    def _rebuild_recent_menu(self):
        self._recent_menu.clear()
        if not self._recent:
            self._recent_menu.addAction("(no recent files)").setEnabled(False)
            return
        for path in self._recent:
            action = self._recent_menu.addAction(os.path.basename(path))
            action.setToolTip(path)
            action.triggered.connect(lambda _, p=path: self.load_pdf(p))
        self._recent_menu.addSeparator()
        self._recent_menu.addAction("Clear Recent", self._clear_recent)

    def _clear_recent(self):
        self._recent.clear()
        self._settings.setValue("recent_files", [])
        self._rebuild_recent_menu()

    # ── presets ──────────────────────────────────

    def _on_save_preset(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Preset", "preset.laydown.json", "Laydown Preset (*.json)")
        if not path:
            return
        from laydown.ui.presets import save_preset
        try:
            save_preset(path, self._store.values())
            self._status.showMessage(f"Preset saved → {os.path.basename(path)}")
        except Exception as exc:
            QMessageBox.critical(self, "Could not save preset", str(exc))

    def _on_load_preset(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Preset", "", "Laydown Preset (*.json);;All Files (*)")
        if not path:
            return
        from laydown.ui.presets import load_preset
        try:
            self._store.load(load_preset(path))
            self._rebuild_collection_editors()
            self._resync_widgets()
            self._status.showMessage(f"Preset loaded — {os.path.basename(path)}")
        except Exception as exc:
            QMessageBox.critical(self, "Could not load preset", str(exc))

    def _on_reset_all(self):
        from laydown.ui.schema import defaults
        values = defaults()
        values["preprocessors"] = []
        values["marks"] = []
        self._store.load(values)
        self._rebuild_collection_editors()

    def _resync_widgets(self):
        values = self._store.values()
        for tab in self._tabs:
            tab.sync_from_store(values)

    def _rebuild_collection_editors(self):
        if "preprocessors" in self._collections:
            self._collections["preprocessors"].set_steps(self._store.get("preprocessors") or [])
        if "marks" in self._collections:
            self._collections["marks"].set_marks(self._store.get("marks") or [])

    # ── export ───────────────────────────────────

    def _on_export(self):
        if not self._source_path:
            return
        project = self.build_project()
        base = os.path.splitext(os.path.basename(self._source_path))[0]
        layout = project.layout
        suffix = "booklet" if layout.layout_type == LayoutType.BOOKLET else f"{layout.nup}up"
        suggested = f"{base}_{suffix}_{project.sheet.preset}.pdf"

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Imposed PDF", suggested, "PDF Files (*.pdf)")
        if not path:
            return

        self._progress = QProgressDialog("Imposing…", "Cancel", 0, 100, self)
        self._progress.setWindowTitle("Generating")
        self._progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress.setMinimumDuration(0)
        self._progress.canceled.connect(self._export.cancel)  # actually stops the work
        self._generate.setEnabled(False)
        self._export.setup(project, path)
        self._export.start()

    def _on_export_progress(self, current, total):
        if not self._progress:
            return
        try:
            self._progress.setValue(int(current / total * 100) if total else 0)
            self._progress.setLabelText(f"Sheet {min(current + 1, total)} of {total}")
        except RuntimeError:
            pass

    def _close_progress(self):
        try:
            if self._progress:
                self._progress.close()
        except RuntimeError:
            pass
        self._progress = None
        self._generate.setEnabled(bool(self._source_path))

    def _on_export_done(self, sheets, path):
        self._close_progress()
        self._status.showMessage(f"Exported {sheets} sheet(s) → {os.path.basename(path)}")
        QMessageBox.information(self, "Export complete",
                                f"Wrote {sheets} sheet(s) to:\n{path}")

    def _on_export_failed(self, message):
        self._close_progress()
        self._status.showMessage(message)
        if message != "Export cancelled":
            QMessageBox.critical(self, "Export failed", message)

    # ── help ─────────────────────────────────────

    def _on_tutorials(self):
        _TutorialsDialog(self).exec()

    def _on_sysdir(self):
        folder = os.path.dirname(os.path.abspath(sys.argv[0]))
        if sys.platform == "win32":
            os.startfile(folder)
        else:
            webbrowser.open(f"file://{folder}")

    def _on_about(self):
        QMessageBox.about(
            self, "About Laydown",
            f"<h2 style='color:{t.ACCENT}'>Laydown {__version__}</h2>"
            "<p>PDF imposition for commercial printing.</p>"
            "<p>Built with Python, PyQt6 and PyMuPDF. Imposition is vector: pages are "
            "embedded, never rasterized.</p>"
            "<p>Licensed under the GNU AGPL v3.0.</p>"
        )

    # ── cleanup ──────────────────────────────────

    def closeEvent(self, event):
        self._close_source_doc()
        self._canvas.cleanup()
        self._export.cancel()
        self._export.wait()
        super().closeEvent(event)
