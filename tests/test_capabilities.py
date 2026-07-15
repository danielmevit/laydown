"""
The UI/engine contract (ROADMAP.md Phase 3).

0.2.0's central defect: the Layout tab collected booklet modes, right-to-left,
signatures and page creep, and the engine ignored every one of them. Nothing was
wrong with either half in isolation — the bug lived in the gap between them, where
no test could see it.

These tests are that gap. They are the reason the defect cannot come back.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pressready.engine.capabilities import (
    HONOURED, NOT_IMPLEMENTED, model_paths, resolve, assign,
)
from pressready.engine.data_model import Project
from pressready.ui.schema import (
    SCHEMA, ControlType, all_controls, all_sections, all_targets, defaults, is_visible,
)


class TestEveryControlIsBackedByTheEngine:
    def test_no_control_promises_something_the_engine_ignores(self):
        offenders = sorted(set(all_targets()) - HONOURED)
        assert not offenders, (
            "these controls edit settings the engine does not read, so the user would "
            f"set them and nothing would happen: {offenders}"
        )

    def test_unimplemented_settings_are_not_offered(self):
        offered = sorted(set(all_targets()) & NOT_IMPLEMENTED)
        assert not offered, (
            f"these settings are declared unimplemented but the UI shows them: {offered}"
        )

    def test_every_control_target_exists_on_the_project(self):
        project = Project()
        for target in all_targets():
            resolve(project, target)  # raises AttributeError if the path is a typo

    def test_a_control_can_actually_write_its_target(self):
        project = Project()
        for control in all_controls():
            if control.type is ControlType.COLLECTION:
                continue
            assign(project, control.target, control.default)
            assert resolve(project, control.target) == control.default


class TestEverySettingIsClassified:
    def test_no_setting_escapes_classification(self):
        # The rule that makes the contract hold over time: adding a field to the data
        # model fails here until someone decides, in public, whether the engine
        # honours it. That decision is what 0.2.0 never had to make.
        unclassified = sorted(model_paths() - HONOURED - NOT_IMPLEMENTED)
        assert not unclassified, (
            "these model settings are neither HONOURED nor NOT_IMPLEMENTED — classify "
            f"them in engine/capabilities.py: {unclassified}"
        )

    def test_classified_settings_all_exist(self):
        project = Project()
        for path in sorted(HONOURED | NOT_IMPLEMENTED):
            resolve(project, path)

    def test_the_two_sets_do_not_overlap(self):
        assert not (HONOURED & NOT_IMPLEMENTED)


class TestSchemaShape:
    def test_control_defaults_match_the_model_defaults(self):
        # The panel's reset must land on the same value a fresh Project has, or
        # "reset" quietly means "change".
        project = Project()
        for control in all_controls():
            if control.type is ControlType.COLLECTION:
                continue
            assert control.default == resolve(project, control.target), (
                f"{control.target}: schema default {control.default!r} != model default "
                f"{resolve(project, control.target)!r}"
            )

    def test_targets_are_unique(self):
        targets = all_targets()
        assert len(targets) == len(set(targets)), "a setting is edited by two controls"

    def test_sections_are_named_for_what_they_edit(self):
        # Toolcraft's rule: a section title names the thing, so the label beside a
        # control can stay short without becoming ambiguous.
        banned = {"settings", "options", "controls", "general", "misc", "other"}
        for section in all_sections():
            assert section.title.lower() not in banned, f"vague section title: {section.title}"
            assert section.entity, f"{section.title} does not say what it edits"

    def test_sections_stay_small_enough_to_read(self):
        for section in all_sections():
            assert 1 <= len(section.controls) <= 7, (
                f"{section.title} has {len(section.controls)} controls; split it"
            )

    def test_section_titles_are_unique(self):
        titles = [s.title for s in all_sections()]
        assert len(titles) == len(set(titles))

    def test_switch_labels_do_not_say_enable(self):
        # The switch already communicates on/off.
        for control in all_controls():
            if control.type is ControlType.SWITCH:
                assert not control.label.lower().startswith("enable"), control.label

    def test_segmented_controls_stay_compact(self):
        for control in all_controls():
            if control.type is not ControlType.SEGMENTED:
                continue
            assert len(control.options) <= 4, f"{control.target}: too many segments"
            for _, text in control.options:
                assert len(text) <= 14, f"{control.target}: segment label {text!r} too long"

    def test_choice_controls_offer_choices(self):
        for control in all_controls():
            if control.type in (ControlType.SEGMENTED, ControlType.SELECT):
                assert len(control.options) >= 2, f"{control.target} has nothing to choose"

    def test_descriptions_add_meaning_beyond_the_label(self):
        for control in all_controls():
            if not control.description:
                continue
            assert control.description.lower() != control.label.lower()
            assert len(control.description) > len(control.label), control.target

    def test_every_tab_has_sections(self):
        for tab in SCHEMA:
            assert tab.sections, f"{tab.name} is empty"


class TestVisibility:
    def test_visibility_conditions_point_at_real_controls(self):
        targets = set(all_targets())
        for item in list(all_controls()) + list(all_sections()):
            if item.visible_when is not None:
                assert item.visible_when.target in targets, (
                    f"visible_when refers to {item.visible_when.target}, which no control owns"
                )

    def test_booklet_controls_are_hidden_for_n_up(self):
        from pressready.engine.data_model import LayoutType
        values = defaults()
        values["layout.layout_type"] = LayoutType.NUP
        booklet = next(s for s in all_sections() if s.title == "Booklet")
        assert not is_visible(booklet, values)

    def test_booklet_controls_appear_for_a_booklet(self):
        from pressready.engine.data_model import LayoutType
        values = defaults()
        values["layout.layout_type"] = LayoutType.BOOKLET
        booklet = next(s for s in all_sections() if s.title == "Booklet")
        assert is_visible(booklet, values)

    def test_signature_size_only_shows_for_perfect_binding(self):
        from pressready.engine.data_model import BookletMode
        values = defaults()
        control = next(c for c in all_controls() if c.target == "layout.signature_sheets")

        values["layout.booklet_mode"] = BookletMode.SADDLE_STITCH
        assert not is_visible(control, values)
        values["layout.booklet_mode"] = BookletMode.PERFECT_BOUND
        assert is_visible(control, values)

    def test_custom_sheet_size_only_shows_for_the_custom_preset(self):
        values = defaults()
        control = next(c for c in all_controls() if c.target == "sheet.custom_width_mm")
        assert not is_visible(control, values)
        values["sheet.preset"] = "Custom"
        assert is_visible(control, values)

    def test_creep_amounts_only_show_when_compensating(self):
        values = defaults()
        control = next(c for c in all_controls() if c.target == "layout.creep_outer_mm")
        assert not is_visible(control, values)
        values["layout.creep_enabled"] = True
        assert is_visible(control, values)
