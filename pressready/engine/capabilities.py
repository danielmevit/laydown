"""
What the engine actually honours.

PressReady 0.2.0 shipped a Layout tab that collected booklet modes, right-to-left,
signatures and page creep, and an engine that silently ignored all of them. The
settings existed, the UI wrote them, nothing read them, and the operator only found
out at the press. That failure was possible because "the model has a field" and
"the engine reads it" were two unrelated facts that nobody checked.

This module makes them one fact. Every setting in the data model is classified
here, and the tests in ``tests/test_capabilities.py`` enforce three rules:

1. every control the UI shows targets an HONOURED setting;
2. every path named here really exists on ``Project``, so typos can't hide;
3. every field of the model is classified — a new setting cannot be added without
   deciding, in public, whether the engine honours it.

Adding a field to the data model therefore *fails the build* until it is listed.
Put it in NOT_IMPLEMENTED and the UI is forbidden from offering it.
"""

from dataclasses import fields, is_dataclass
from typing import Any, Set

from pressready.engine.data_model import Project


# Settings the engine reads and acts on. The UI may offer these.
HONOURED: Set[str] = {
    "source_pdf_path",

    # Source pages — engine/geometry.source_boxes
    "source.box",
    "source.bleed_mm",

    # Preprocessors — engine/preprocessors.apply_preprocessors
    "preprocessors",

    # Layout — engine/geometry.sheet_plan
    "layout.layout_type",
    "layout.nup",
    "layout.rows",
    "layout.cols",
    "layout.auto_rotate",
    "layout.booklet_mode",
    "layout.signature_sheets",
    "layout.right_to_left",
    "layout.fillers_in_middle",
    "layout.gutter_h_mm",
    "layout.gutter_v_mm",
    "layout.page_range",
    "layout.creep_enabled",
    "layout.creep_outer_mm",
    "layout.creep_inner_mm",

    # Sheet — engine/geometry.sheet_size_pt, margins_pt
    "sheet.preset",
    "sheet.custom_width_mm",
    "sheet.custom_height_mm",
    "sheet.orientation",
    "sheet.margin_top_mm",
    "sheet.margin_bottom_mm",
    "sheet.margin_left_mm",
    "sheet.margin_right_mm",

    # Marks — engine/marks.draw_marks
    "marks",
}


# Declared in the model but not implemented. The UI must NOT offer these: a control
# that cannot do anything is worse than a missing feature, because the operator
# believes it worked. Move an entry up to HONOURED in the same change that makes the
# engine read it, never before.
NOT_IMPLEMENTED: Set[str] = set()


def _walk(obj: Any, prefix: str = "") -> Set[str]:
    """Every settable path in the model tree, dotted."""
    found: Set[str] = set()
    for f in fields(obj):
        path = f"{prefix}{f.name}"
        value = getattr(obj, f.name)
        if is_dataclass(value) and not isinstance(value, type):
            found |= _walk(value, f"{path}.")
        else:
            found.add(path)
    return found


def model_paths() -> Set[str]:
    """Every setting the data model exposes, discovered by walking a default Project."""
    return _walk(Project())


def resolve(project: Project, path: str) -> Any:
    """Read a dotted path off a Project. Raises AttributeError if it doesn't exist."""
    value: Any = project
    for part in path.split("."):
        value = getattr(value, part)
    return value


def assign(project: Project, path: str, value: Any) -> None:
    """Write a dotted path on a Project."""
    parts = path.split(".")
    target = project
    for part in parts[:-1]:
        target = getattr(target, part)
    setattr(target, parts[-1], value)
