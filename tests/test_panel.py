"""
The panel machinery: one value store behind every control (ROADMAP.md Phase 3).

Because all settings live in one dict keyed by schema target, undo, per-section
reset, presets and building a Project are all the same small operation. These tests
hold that, and hold the rule that a control which can't act is hidden rather than
shown greyed out.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from pressready.engine.data_model import (
    BookletMode, LayoutType, MarkItem, MarkType, Orientation, PreprocessorStep,
    PreprocessorType, Project, SourceBox,
)
from pressready.ui.panel import SchemaTab, ValueStore
from pressready.ui.presets import load_preset, save_preset
from pressready.ui.schema import SCHEMA, defaults


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def store(app):
    return ValueStore()


class TestValueStore:
    def test_starts_at_the_schema_defaults(self, store):
        assert store.get("layout.nup") == 2
        assert store.get("source.box") is SourceBox.TRIM
        assert store.get("sheet.preset") == "A3"

    def test_setting_a_value_emits_once(self, store):
        seen = []
        store.changed.connect(lambda: seen.append(1))
        store.set("layout.nup", 4)
        assert store.get("layout.nup") == 4
        assert len(seen) == 1

    def test_setting_the_same_value_is_not_a_change(self, store):
        seen = []
        store.changed.connect(lambda: seen.append(1))
        store.set("layout.nup", 2)  # already 2
        assert not seen

    def test_builds_a_project_from_dotted_targets(self, store):
        store.set("layout.nup", 4)
        store.set("sheet.orientation", Orientation.PORTRAIT)
        store.set("source.bleed_mm", 3.0)
        project = store.to_project("/tmp/x.pdf")

        assert isinstance(project, Project)
        assert project.layout.nup == 4
        assert project.sheet.orientation is Orientation.PORTRAIT
        assert project.source.bleed_mm == 3.0
        assert project.source_pdf_path == "/tmp/x.pdf"

    def test_project_carries_the_collections(self, store):
        store.set("marks", [MarkItem(mark_type=MarkType.CROP_MARKS)])
        store.set("preprocessors",
                  [PreprocessorStep(type=PreprocessorType.ROTATE_PAGES)])
        project = store.to_project()
        assert len(project.marks) == 1
        assert project.marks[0].mark_type is MarkType.CROP_MARKS
        assert len(project.preprocessors) == 1

    def test_a_project_does_not_alias_the_store(self, store):
        store.set("marks", [MarkItem(mark_type=MarkType.CROP_MARKS)])
        project = store.to_project()
        project.marks[0].enabled = False
        assert store.get("marks")[0].enabled is True, "the store was mutated through a Project"

    def test_every_default_project_matches_a_fresh_project(self, store):
        assert store.to_project().layout == Project().layout
        assert store.to_project().sheet == Project().sheet
        assert store.to_project().source == Project().source


class TestHistory:
    def test_undo_restores_the_previous_value(self, store):
        store.set("layout.nup", 4)
        store.set("layout.nup", 9)
        store.undo()
        assert store.get("layout.nup") == 4
        store.undo()
        assert store.get("layout.nup") == 2

    def test_redo_reapplies(self, store):
        store.set("layout.nup", 4)
        store.undo()
        store.redo()
        assert store.get("layout.nup") == 4

    def test_nothing_to_undo_at_the_start(self, store):
        assert not store.can_undo()
        assert not store.can_redo()
        store.undo()  # must not raise
        assert store.get("layout.nup") == 2

    def test_a_new_edit_clears_the_redo_stack(self, store):
        store.set("layout.nup", 4)
        store.undo()
        assert store.can_redo()
        store.set("layout.nup", 9)
        assert not store.can_redo()


class TestSectionReset:
    def test_reset_restores_only_the_named_targets(self, store):
        store.set("layout.gutter_h_mm", 12.0)
        store.set("sheet.preset", "A2")
        store.reset_targets(["layout.gutter_h_mm"])
        assert store.get("layout.gutter_h_mm") == 0.0
        assert store.get("sheet.preset") == "A2", "reset leaked into another section"

    def test_reset_is_undoable(self, store):
        store.set("layout.gutter_h_mm", 12.0)
        store.reset_targets(["layout.gutter_h_mm"])
        store.undo()
        assert store.get("layout.gutter_h_mm") == 12.0


class TestPresets:
    def test_round_trip_preserves_every_setting(self, store, tmp_path):
        store.set("layout.layout_type", LayoutType.BOOKLET)
        store.set("layout.booklet_mode", BookletMode.PERFECT_BOUND)
        store.set("layout.signature_sheets", 8)
        store.set("source.box", SourceBox.BLEED)
        store.set("source.bleed_mm", 4.5)
        store.set("sheet.preset", "Custom")
        store.set("sheet.custom_width_mm", 700.0)
        store.set("marks", [MarkItem(mark_type=MarkType.CROP_MARKS, crop_length_mm=7.0)])
        expected = store.values()

        path = str(tmp_path / "p.json")
        save_preset(path, expected)
        restored = ValueStore()
        restored.load(load_preset(path))

        assert restored.get("layout.booklet_mode") is BookletMode.PERFECT_BOUND
        assert restored.get("source.box") is SourceBox.BLEED
        assert restored.get("source.bleed_mm") == 4.5
        assert restored.get("sheet.custom_width_mm") == 700.0
        assert restored.get("marks")[0].mark_type is MarkType.CROP_MARKS
        assert restored.get("marks")[0].crop_length_mm == 7.0
        assert restored.to_project().layout == store.to_project().layout

    def test_preset_is_human_readable_json(self, store, tmp_path):
        path = str(tmp_path / "p.json")
        save_preset(path, store.values())
        text = open(path, encoding="utf-8").read()
        assert '"application": "PressReady"' in text
        assert "TRIM" in text, "enums should be written by name, not as an opaque number"

    def test_unknown_keys_are_ignored(self, tmp_path):
        import json
        path = tmp_path / "p.json"
        path.write_text(json.dumps({
            "format": 1, "values": {"layout.nup": 4, "layout.from_the_future": 99}}))
        values = load_preset(str(path))
        assert values["layout.nup"] == 4
        assert "layout.from_the_future" not in values

    def test_a_newer_format_is_refused_clearly(self, tmp_path):
        import json
        path = tmp_path / "p.json"
        path.write_text(json.dumps({"format": 99, "values": {}}))
        with pytest.raises(ValueError, match="newer PressReady"):
            load_preset(str(path))

    def test_a_non_preset_is_refused(self, tmp_path):
        path = tmp_path / "p.json"
        path.write_text('{"hello": 1}')
        with pytest.raises(ValueError, match="not a PressReady preset"):
            load_preset(str(path))


class TestRenderedPanel:
    def test_every_tab_builds(self, app, store):
        for tab in SCHEMA:
            page = SchemaTab(tab, store)
            page.refresh(store.values())

    def test_booklet_section_hides_itself_for_n_up(self, app, store):
        layout_tab = next(t for t in SCHEMA if t.name == "Layout")
        page = SchemaTab(layout_tab, store)

        store.set("layout.layout_type", LayoutType.NUP)
        page.refresh(store.values())
        booklet = next(s for s in page.sections if s.section.title == "Booklet")
        assert not booklet.isVisible()

        store.set("layout.layout_type", LayoutType.BOOKLET)
        page.refresh(store.values())
        assert booklet.isVisibleTo(page), "booklet settings never appeared"

    def test_hidden_controls_are_hidden_not_disabled(self, app, store):
        # The rule that answers 0.2.0's defect: a control that cannot act is gone,
        # not greyed out. A greyed control still says "this feature exists".
        layout_tab = next(t for t in SCHEMA if t.name == "Layout")
        page = SchemaTab(layout_tab, store)
        store.set("layout.layout_type", LayoutType.BOOKLET)
        store.set("layout.booklet_mode", BookletMode.SADDLE_STITCH)
        page.refresh(store.values())

        booklet = next(s for s in page.sections if s.section.title == "Booklet")
        for control, widget in booklet._rows:
            if control.target == "layout.signature_sheets":
                assert not widget.isVisible()
                assert widget.isEnabled(), "hidden controls must not also be disabled"

    def test_editing_a_widget_writes_through_to_the_store(self, app, store):
        sheet_tab = next(t for t in SCHEMA if t.name == "Sheet")
        page = SchemaTab(sheet_tab, store)
        margins = next(s for s in page.sections if s.section.title == "Margins")
        control, row = margins._rows[0]
        row.widget.setValue(11.0)
        assert store.get(control.target) == 11.0


class TestCollectionEditors:
    """
    The two growable lists keep bespoke editors. Their per-item settings panel is
    easy to break silently — an edit once absorbed `_setup_ui`'s trailing
    `setVisible(False)` into the browse handler, so the panel showed empty at
    startup and vanished after picking a file. Neither is visible to an engine test.
    """

    def test_marks_editor_starts_with_no_item_panel(self, app):
        from pressready.ui.marks_tab import MarksTab
        editor = MarksTab()
        assert not editor._settings_group.isVisible()

    def test_preprocessors_editor_starts_with_no_item_panel(self, app):
        from pressready.ui.preprocessors_tab import PreprocessorsTab
        editor = PreprocessorsTab()
        assert not editor._settings_group.isVisible()

    def test_selecting_a_mark_reveals_its_settings(self, app):
        from pressready.ui.marks_tab import MarksTab
        editor = MarksTab()
        editor.set_marks([MarkItem(mark_type=MarkType.CROP_MARKS)])
        editor._list.setCurrentRow(0)
        assert editor._settings_group.isVisibleTo(editor)

    def test_browsing_for_mark_artwork_does_not_hide_the_settings(self, app, tmp_path, monkeypatch):
        from PyQt6.QtWidgets import QFileDialog
        from pressready.ui.marks_tab import MarksTab
        art = tmp_path / "mark.pdf"
        art.write_bytes(b"%PDF-1.4")
        editor = MarksTab()
        editor.set_marks([MarkItem(mark_type=MarkType.CUSTOM_MARK)])
        editor._list.setCurrentRow(0)
        monkeypatch.setattr(QFileDialog, "getOpenFileName",
                            staticmethod(lambda *a, **k: (str(art), "")))
        editor._on_browse_mark()
        assert editor._mark_path.text() == str(art)
        assert editor._settings_group.isVisibleTo(editor)
        assert editor.get_marks()[0].mark_pdf_path == str(art)

    def test_every_mark_type_is_offered(self, app):
        from pressready.ui.marks_tab import MarksTab
        editor = MarksTab()
        offered = {editor._add_combo.itemData(i) for i in range(editor._add_combo.count())}
        assert offered == set(MarkType), "a mark the engine draws is not reachable from the UI"


class TestWidgetsFollowTheStore:
    """
    Undo, redo and preset loads change the store underneath the widgets. Every
    control must be pushed the new value — not just the ones that were easy to
    wire. This regressed once: only length fields resynced, so undoing a booklet
    change left the segmented control showing the old binding while the store, the
    preview and the exported PDF all had the new one.
    """

    def _layout_tab(self, store):
        return SchemaTab(next(t for t in SCHEMA if t.name == "Layout"), store)

    def _bound(self, page, target):
        for section in page.sections:
            if target in section._bound:
                return section._bound[target]
        raise AssertionError(f"no widget bound to {target}")

    def test_segmented_follows_an_undo(self, app, store):
        page = self._layout_tab(store)
        store.set("layout.layout_type", LayoutType.BOOKLET)
        page.sync_from_store(store.values())
        assert self._bound(page, "layout.layout_type").value() is LayoutType.BOOKLET

        store.undo()
        page.sync_from_store(store.values())
        assert self._bound(page, "layout.layout_type").value() is LayoutType.NUP, (
            "the Type control still shows Booklet after undoing back to N-Up"
        )

    def test_switch_follows_the_store(self, app, store):
        page = self._layout_tab(store)
        store.set("layout.right_to_left", True)
        page.sync_from_store(store.values())
        assert self._bound(page, "layout.right_to_left").isChecked()
        store.undo()
        page.sync_from_store(store.values())
        assert not self._bound(page, "layout.right_to_left").isChecked()

    def test_select_follows_the_store(self, app, store):
        page = SchemaTab(next(t for t in SCHEMA if t.name == "Layout"), store)
        store.set("layout.nup", 9)
        page.sync_from_store(store.values())
        assert self._bound(page, "layout.nup").currentData() == 9

    def test_text_follows_the_store(self, app, store):
        page = self._layout_tab(store)
        store.set("layout.page_range", "1-4,7")
        page.sync_from_store(store.values())
        assert self._bound(page, "layout.page_range").text() == "1-4,7"

    def test_length_follows_the_store(self, app, store):
        page = self._layout_tab(store)
        store.set("layout.gutter_h_mm", 7.5)
        page.sync_from_store(store.values())
        assert self._bound(page, "layout.gutter_h_mm").mm() == 7.5

    def test_syncing_does_not_write_back_to_the_store(self, app, store):
        # A resync must not look like a user edit, or undo would never terminate.
        page = self._layout_tab(store)
        store.set("layout.gutter_h_mm", 7.5)
        before = len(store._undo)
        page.sync_from_store(store.values())
        assert len(store._undo) == before

    def test_a_preset_load_reaches_every_control(self, app, store, tmp_path):
        store.set("layout.layout_type", LayoutType.BOOKLET)
        store.set("layout.booklet_mode", BookletMode.PERFECT_BOUND)
        store.set("layout.right_to_left", True)
        store.set("layout.page_range", "2-8")
        path = str(tmp_path / "p.json")
        save_preset(path, store.values())

        fresh = ValueStore()
        page = self._layout_tab(fresh)
        fresh.load(load_preset(path))
        page.sync_from_store(fresh.values())

        assert self._bound(page, "layout.layout_type").value() is LayoutType.BOOKLET
        assert self._bound(page, "layout.booklet_mode").value() is BookletMode.PERFECT_BOUND
        assert self._bound(page, "layout.right_to_left").isChecked()
        assert self._bound(page, "layout.page_range").text() == "2-8"

    def test_every_non_collection_control_is_bound(self, app, store):
        # If a control isn't in _bound it can never be resynced — which is exactly
        # how the segmented control got missed.
        from pressready.ui.schema import ControlType
        for tab in SCHEMA:
            page = SchemaTab(tab, store)
            bound = set().union(*(s._bound.keys() for s in page.sections)) if page.sections else set()
            for section in tab.sections:
                for control in section.controls:
                    if control.type is ControlType.COLLECTION:
                        continue
                    assert control.target in bound, f"{control.target} is not resyncable"
