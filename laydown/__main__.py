"""Laydown entry point.  Run with: python -m laydown"""

import argparse
import os
import sys

from laydown import __version__

os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.fonts.warning=false")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="laydown",
        description="Laydown — PDF imposition for commercial printing.",
    )
    p.add_argument("pdf", nargs="?", help="PDF to open on startup")
    p.add_argument(
        "--smoke", action="store_true",
        help="run a headless end-to-end self-check and exit (0 = healthy, 1 = broken)",
    )
    p.add_argument("--version", action="version", version=f"Laydown {__version__}")
    return p


def _claim_windows_taskbar_identity() -> None:
    """Give the *unpackaged* Windows build (portable ZIP / loose exe) its own taskbar
    identity so Windows groups its windows under one button and draws our window icon
    on it.

    Two traps this avoids:

    * The identity must NOT equal the MSIX package identity (``LaydownTeam.Laydown``).
      When it did, a user who also had the MSIX/Store build installed got a *blank*
      taskbar button for the portable: Windows resolved the taskbar icon through that
      installed package — which the portable isn't running inside — and found nothing.
    * A packaged (MSIX) run already gets its identity from the package. Overriding it
      would break the Store app's identity, so we only set one when NOT inside a package.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        # GetCurrentPackageFullName returns APPMODEL_ERROR_NO_PACKAGE (15700) when the
        # process is running unpackaged; anything else means we're inside an MSIX.
        length = wintypes.UINT(0)
        rc = ctypes.windll.kernel32.GetCurrentPackageFullName(ctypes.byref(length), None)
        if rc == 15700:  # unpackaged -> claim a distinct identity of our own
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "DanielMevit.Laydown")
    except Exception:
        # A taskbar identity is a nicety; never crash startup over it. Without it the
        # taskbar simply falls back to the exe's own embedded icon, which is fine.
        pass


def _write_icon_debug(app) -> None:
    """TEMPORARY diagnostic. A windowed PyInstaller build has no stdout, so to trace a
    blank-icon report we dump how the icon actually resolves at runtime to a file next
    to the exe (and the home dir as backup). Remove before the real release."""
    try:
        import pathlib
        from PyQt6.QtGui import QPixmap
        from laydown.ui.main_window import app_icon

        lines = [
            f"Laydown {__version__} icon diagnostic",
            f"platform={sys.platform}  frozen={getattr(sys, 'frozen', False)}",
            f"_MEIPASS={getattr(sys, '_MEIPASS', None)}",
            f"executable={sys.executable}",
            "",
        ]
        roots = []
        if getattr(sys, "frozen", False):
            mp = getattr(sys, "_MEIPASS", None)
            if mp:
                roots.append(pathlib.Path(mp) / "assets" / "icons")
            ed = pathlib.Path(sys.executable).resolve().parent
            roots.append(ed / "assets" / "icons")
            roots.append(ed / "_internal" / "assets" / "icons")
        roots.append(
            pathlib.Path(__file__).resolve().parent.parent.parent / "assets" / "icons")
        for r in roots:
            p = r / "icon_32x32.png"
            lines.append(f"root {r}\n    dir={r.exists()} icon32={p.exists()}")
            if p.exists():
                pm = QPixmap(str(p))
                lines.append(f"    QPixmap isNull={pm.isNull()} {pm.width()}x{pm.height()}")
        ic = app_icon()
        lines += [
            "",
            f"app_icon().isNull()={ic.isNull()}",
            f"app_icon sizes={[(s.width(), s.height()) for s in ic.availableSizes()]}",
            f"app.windowIcon().isNull()={app.windowIcon().isNull()}",
        ]
        text = "\n".join(lines)
        for target in (
            pathlib.Path(sys.executable).resolve().parent / "laydown-icon-debug.txt",
            pathlib.Path.home() / "laydown-icon-debug.txt",
        ):
            try:
                target.write_text(text, encoding="utf-8")
            except Exception:
                pass
    except Exception:
        pass


def run_gui(pdf: str = "") -> int:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QFont

    from laydown.ui import theme
    from laydown.ui.main_window import MainWindow, app_icon

    _claim_windows_taskbar_identity()

    app = QApplication(sys.argv)
    theme.apply(app)
    app.setApplicationName("Laydown")
    app.setApplicationVersion(__version__)
    app.setWindowIcon(app_icon())
    _write_icon_debug(app)   # TEMPORARY — remove before release
    app.setFont(QFont("Segoe UI", 9))

    win = MainWindow()
    win.show()
    if pdf:
        win.load_pdf(pdf)
    return app.exec()


def run_smoke() -> int:
    """
    Headless end-to-end check: build a sample PDF, impose it, read the result back,
    then construct the real window offscreen and drive it through a load.

    Exists so the whole stack is verifiable without eyes — in CI, in a frozen build,
    or from WSL where the GUI can't run (see docs/ai/GOTCHAS.md).
    """
    import tempfile
    import traceback

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    done = []

    try:
        import fitz

        from laydown.engine.data_model import (
            Project, LayoutSettings, LayoutType, SheetSettings, Orientation,
            MarkItem, MarkType,
        )
        from laydown.engine.impose import impose
        from laydown.engine.utils import mm_to_pt

        with tempfile.TemporaryDirectory() as tmp:
            # 1. a sample source, built rather than bundled so nothing can go stale
            src = os.path.join(tmp, "sample.pdf")
            doc = fitz.open()
            for i in range(1, 5):
                page = doc.new_page(width=mm_to_pt(210), height=mm_to_pt(297))
                page.insert_text((72, 96), f"Laydown smoke page {i}", fontsize=18)
                page.draw_rect(page.rect + (20, 20, -20, -20), color=(0.3, 0.3, 0.3), width=0.8)
            doc.save(src)
            doc.close()
            done.append("built a 4-page A4 sample")

            # 2. impose it the way the app would
            project = Project(source_pdf_path=src)
            project.sheet = SheetSettings(preset="A3", orientation=Orientation.LANDSCAPE)
            project.layout = LayoutSettings(layout_type=LayoutType.NUP, nup=2)
            project.marks = [
                MarkItem(mark_type=MarkType.CROP_MARKS),
                MarkItem(mark_type=MarkType.TEXT_LABEL),
            ]
            out = os.path.join(tmp, "imposed.pdf")
            sheets = impose(project, out)
            done.append(f"imposed 2-up on A3 -> {sheets} sheet(s)")

            # 3. read the output back
            result = fitz.open(out)
            if len(result) != 2:
                raise AssertionError(f"expected 2 sheets, got {len(result)}")
            width = result[0].rect.width
            if abs(width - mm_to_pt(420)) > 1.0:
                raise AssertionError(f"expected an A3-landscape sheet, got width {width:.1f}pt")
            words = {w[4] for w in result[0].get_text("words")}
            if "Laydown" not in words:
                raise AssertionError("imposed sheet carries none of the source text")
            result.close()
            done.append("verified sheet count, sheet size and placed content")

            # 4. the real window, offscreen
            from PyQt6.QtWidgets import QApplication

            from laydown.ui.main_window import MainWindow

            app = QApplication.instance() or QApplication([])
            win = MainWindow()
            win.load_pdf(src)
            built = win.build_project()
            if built.source_pdf_path != src:
                raise AssertionError("main window did not take the loaded PDF")
            win.close()
            del app
            done.append("built the main window offscreen and loaded a PDF")

    except Exception:
        traceback.print_exc()
        for step in done:
            print(f"  ok   {step}")
        print("SMOKE FAIL", file=sys.stderr)
        return 1

    for step in done:
        print(f"  ok   {step}")
    print(f"SMOKE OK — Laydown {__version__}")
    return 0


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    if args.smoke:
        return run_smoke()
    return run_gui(args.pdf or "")


if __name__ == "__main__":
    sys.exit(main())
