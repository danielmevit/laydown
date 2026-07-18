"""
The Lucide icon set (ROADMAP: 0.4.1 UI icons).

A mistyped icon name would sail past every engine test and then crash when the
main window is built — these guard the name↔geometry contract from the one place
that runs headless everywhere.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from laydown.ui import icons


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class TestIconRenderer:
    def test_every_registered_icon_renders_non_null(self, app):
        for name in icons.names():
            icon = icons.lucide(name, 24, "#D07B24")
            assert not icon.isNull(), f"{name} rendered nothing"

    def test_unknown_name_is_a_clear_error(self, app):
        with pytest.raises(KeyError, match="no Lucide icon"):
            icons.lucide("does-not-exist")

    def test_colour_reaches_the_pixels(self, app):
        # Prove the stroke colour is honoured, so a themed icon isn't silently black.
        from PyQt6.QtGui import QColor
        pm = icons.lucide("zoom_in", 48, "#D07B24").pixmap(48, 48)
        img = pm.toImage()
        seen = {img.pixelColor(x, y).name()
                for x in range(0, 48, 2) for y in range(0, 48, 2)
                if img.pixelColor(x, y).alpha() > 200}
        # Antialiasing produces intermediate tones; the orange must dominate the
        # opaque stroke pixels, not black.
        oranges = [c for c in seen if QColor(c).redF() > QColor(c).blueF() + 0.15]
        assert oranges, f"no orange stroke pixels found, got {sorted(seen)[:6]}"


class TestWiredIntoTheWindow:
    def test_toolbar_and_tab_icon_names_all_exist(self, app):
        # main_window references icons by name; a typo there crashes construction.
        from laydown.ui import main_window as mw
        registered = set(icons.names())
        for name in mw._TAB_ICON_NAMES:
            assert name in registered, f"tab icon {name!r} is not registered"

    def test_app_icon_is_never_empty(self, app):
        # An empty window icon is what leaves the Windows taskbar button blank. The
        # loader tries several roots and falls back to the .ico, so it must always
        # return something with real sizes — in a checkout and in a frozen bundle.
        from laydown.ui.main_window import app_icon
        icon = app_icon()
        assert not icon.isNull(), "app icon is empty; the taskbar button would be blank"
        sizes = {(s.width(), s.height()) for s in icon.availableSizes()}
        assert sizes, "app icon carries no sizes"
        assert max(w for w, _ in sizes) >= 32, f"app icon has only tiny sizes: {sizes}"

    def test_the_window_builds_with_every_icon_present(self, app):
        from laydown.ui.main_window import MainWindow
        w = MainWindow()
        assert len(w._tab_buttons) == 4
        assert all(not b.icon().isNull() for b in w._tab_buttons)
        assert not w._generate.icon().isNull()
        w.close()

    def test_tab_icons_are_centred_in_their_buttons(self, app):
        # A QTabBar left-biases an icon-only tab by ~7px (0.4.3 and earlier); the
        # QToolButton strip centres each glyph. Guards the regression.
        from laydown.ui.main_window import MainWindow
        w = MainWindow()
        w.resize(1600, 980)
        w.show()
        app.processEvents()
        for i, btn in enumerate(w._tab_buttons):
            img = btn.grab().toImage()
            width, height = img.width(), img.height()
            xs = [x for x in range(width) for y in range(0, height, 2)
                  if img.pixelColor(x, y).alpha() > 60]
            assert xs, f"tab {i} drew no icon"
            offset = sum(xs) / len(xs) - width / 2
            assert abs(offset) < 4, f"tab {i} icon off-centre by {offset:.1f}px"
        w.close()
