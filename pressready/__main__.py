"""PressReady v2 entry point.  Run with: python -m pressready"""

import argparse
import os
import sys

from pressready import __version__

os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.fonts.warning=false")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pressready",
        description="PressReady — PDF imposition for commercial printing.",
    )
    p.add_argument("pdf", nargs="?", help="PDF to open on startup")
    p.add_argument(
        "--smoke", action="store_true",
        help="run a headless end-to-end self-check and exit (0 = healthy, 1 = broken)",
    )
    p.add_argument("--version", action="version", version=f"PressReady {__version__}")
    return p


def run_gui(pdf: str = "") -> int:
    import ctypes

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QFont

    from pressready.ui.main_window import MainWindow, app_icon

    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("pressready.v2")

    app = QApplication(sys.argv)
    app.setApplicationName("PressReady")
    app.setApplicationVersion(__version__)
    app.setWindowIcon(app_icon())
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

        from pressready.engine.data_model import (
            Project, LayoutSettings, LayoutType, SheetSettings, Orientation,
            MarkItem, MarkType,
        )
        from pressready.engine.impose import impose
        from pressready.engine.utils import mm_to_pt

        with tempfile.TemporaryDirectory() as tmp:
            # 1. a sample source, built rather than bundled so nothing can go stale
            src = os.path.join(tmp, "sample.pdf")
            doc = fitz.open()
            for i in range(1, 5):
                page = doc.new_page(width=mm_to_pt(210), height=mm_to_pt(297))
                page.insert_text((72, 96), f"PressReady smoke page {i}", fontsize=18)
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
            if "PressReady" not in words:
                raise AssertionError("imposed sheet carries none of the source text")
            result.close()
            done.append("verified sheet count, sheet size and placed content")

            # 4. the real window, offscreen
            from PyQt6.QtWidgets import QApplication

            from pressready.ui.main_window import MainWindow

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
    print(f"SMOKE OK — PressReady {__version__}")
    return 0


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    if args.smoke:
        return run_smoke()
    return run_gui(args.pdf or "")


if __name__ == "__main__":
    sys.exit(main())
