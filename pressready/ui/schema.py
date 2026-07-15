"""
The settings panel, declared rather than wired.

Every control the user sees is described here once: what it edits (``target``, a
dotted path into ``Project``), how it renders, its default, and when it applies.
``ui/panel.py`` turns this into widgets; nothing else builds settings UI by hand.

Two rules carry most of the weight, both learned from the Toolcraft study
(docs/ai/REFERENCE_STUDY.md):

* **Every target must be honoured by the engine.** Enforced by a test against
  ``engine/capabilities.HONOURED``. A control that does nothing fails the build,
  which is the defect 0.2.0 shipped.
* **Hide, never disable.** A setting that doesn't apply to the current mode is
  removed via ``visible_when`` instead of being greyed out, so the panel only ever
  shows controls that can actually do something.

Section titles name the thing being edited (``Booklet``, `Bleed`), never
``Settings`` or ``Options``.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Sequence, Tuple

from pressready.engine.data_model import (
    BookletMode, LayoutType, Orientation, SourceBox, SHEET_PRESETS_MM,
)


class ControlType(Enum):
    SEGMENTED = "segmented"    # full-width, finite, ≤4 short options
    SELECT = "select"          # dropdown
    SWITCH = "switch"          # binary
    NUMBER = "number"          # spin box
    TEXT = "text"              # single line
    COLLECTION = "collection"  # growable list with its own editor


@dataclass(frozen=True)
class When:
    """A visibility condition on another control's value."""
    target: str
    equals: Any = None
    one_of: Optional[Tuple[Any, ...]] = None

    def holds(self, value: Any) -> bool:
        if self.one_of is not None:
            return value in self.one_of
        return value == self.equals


@dataclass(frozen=True)
class Control:
    type: ControlType
    target: str
    label: str
    default: Any = None
    description: str = ""          # only when it adds meaning beyond the label
    options: Tuple[Tuple[Any, str], ...] = ()
    minimum: float = 0.0
    maximum: float = 1000.0
    step: float = 1.0
    decimals: int = 0
    suffix: str = ""
    placeholder: str = ""
    visible_when: Optional[When] = None


@dataclass(frozen=True)
class Section:
    title: str
    entity: str                    # the product thing these controls edit
    controls: Tuple[Control, ...]
    visible_when: Optional[When] = None


@dataclass(frozen=True)
class Tab:
    name: str
    sections: Tuple[Section, ...]


def _enum_options(enum_cls) -> Tuple[Tuple[Any, str], ...]:
    return tuple((member, member.value) for member in enum_cls)


_PRESET_OPTIONS = tuple((k, k) for k in SHEET_PRESETS_MM) + (("Custom", "Custom"),)

_IS_BOOKLET = When(target="layout.layout_type", equals=LayoutType.BOOKLET)
_IS_NUP = When(target="layout.layout_type", equals=LayoutType.NUP)


SCHEMA: Tuple[Tab, ...] = (
    Tab(
        name="Source",
        sections=(
            Section(
                title="Page Box",
                entity="the incoming pages",
                controls=(
                    Control(
                        type=ControlType.SELECT,
                        target="source.box",
                        label="Impose",
                        default=SourceBox.TRIM,
                        description=(
                            "Which box of the source page is fitted to each cell. Trim is "
                            "the finished page a press-ready PDF describes; it falls back "
                            "to the full page when the file carries no boxes."
                        ),
                        options=_enum_options(SourceBox),
                    ),
                    Control(
                        type=ControlType.NUMBER,
                        target="source.bleed_mm",
                        label="Bleed",
                        default=0.0,
                        description=(
                            "Extra artwork pulled beyond the box and allowed to spill "
                            "outside the cell, so a slightly off cut still lands on ink."
                        ),
                        maximum=50.0, decimals=1, step=0.5, suffix=" mm",
                    ),
                ),
            ),
            Section(
                title="Preprocessors",
                entity="transforms applied before imposition",
                controls=(
                    Control(
                        type=ControlType.COLLECTION,
                        target="preprocessors",
                        label="Steps",
                    ),
                ),
            ),
        ),
    ),
    Tab(
        name="Layout",
        sections=(
            Section(
                title="Arrangement",
                entity="how pages are placed on the sheet",
                controls=(
                    Control(
                        type=ControlType.SEGMENTED,
                        target="layout.layout_type",
                        label="Type",
                        default=LayoutType.NUP,
                        options=_enum_options(LayoutType),
                    ),
                    Control(
                        type=ControlType.SELECT,
                        target="layout.nup",
                        label="Pages per sheet",
                        default=2,
                        options=((1, "1-Up"), (2, "2-Up"), (4, "4-Up"), (6, "6-Up"),
                                 (8, "8-Up"), (9, "9-Up"), (16, "16-Up")),
                        visible_when=_IS_NUP,
                    ),
                    Control(
                        type=ControlType.SWITCH,
                        target="layout.auto_rotate",
                        label="Turn pages to fit",
                        default=False,
                        description=(
                            "Rotate a page a quarter turn when that fills its cell better — "
                            "landscape artwork on a portrait sheet."
                        ),
                        visible_when=_IS_NUP,
                    ),
                ),
            ),
            Section(
                title="Booklet",
                entity="how folded sheets become a book",
                visible_when=_IS_BOOKLET,
                controls=(
                    Control(
                        type=ControlType.SEGMENTED,
                        target="layout.booklet_mode",
                        label="Binding",
                        default=BookletMode.SADDLE_STITCH,
                        description=(
                            "Saddle stitch nests every sheet into one signature and staples "
                            "the fold. Perfect binding folds fixed-size signatures separately "
                            "and glues them, which changes the page order."
                        ),
                        options=_enum_options(BookletMode),
                    ),
                    Control(
                        type=ControlType.NUMBER,
                        target="layout.signature_sheets",
                        label="Sheets per signature",
                        default=4,
                        minimum=1, maximum=64, step=1,
                        visible_when=When(target="layout.booklet_mode",
                                          equals=BookletMode.PERFECT_BOUND),
                    ),
                    Control(
                        type=ControlType.SWITCH,
                        target="layout.right_to_left",
                        label="Right-to-left binding",
                        default=False,
                    ),
                    Control(
                        type=ControlType.SWITCH,
                        target="layout.fillers_in_middle",
                        label="Blanks in the middle",
                        default=False,
                        description=(
                            "A booklet pads out to a multiple of four. Put the blanks at the "
                            "centre spread instead of the end, to keep a printed back cover."
                        ),
                    ),
                ),
            ),
            Section(
                title="Creep",
                entity="fore-edge compensation",
                visible_when=_IS_BOOKLET,
                controls=(
                    Control(
                        type=ControlType.SWITCH,
                        target="layout.creep_enabled",
                        label="Compensate",
                        default=False,
                        description=(
                            "Nested sheets push out at the fore-edge, and trimming the folded "
                            "stack flush takes more off the inner leaves. This walks each "
                            "sheet's pages towards the spine to even the margins out."
                        ),
                    ),
                    Control(
                        type=ControlType.NUMBER,
                        target="layout.creep_outer_mm",
                        label="Outer sheet",
                        default=0.0,
                        minimum=-50.0, maximum=50.0, decimals=2, step=0.1, suffix=" mm",
                        visible_when=When(target="layout.creep_enabled", equals=True),
                    ),
                    Control(
                        type=ControlType.NUMBER,
                        target="layout.creep_inner_mm",
                        label="Inner sheet",
                        default=0.0,
                        description="The innermost sheet creeps most; the rest interpolate.",
                        minimum=-50.0, maximum=50.0, decimals=2, step=0.1, suffix=" mm",
                        visible_when=When(target="layout.creep_enabled", equals=True),
                    ),
                ),
            ),
            Section(
                title="Gutters",
                entity="the gaps between cells",
                controls=(
                    Control(
                        type=ControlType.NUMBER,
                        target="layout.gutter_h_mm",
                        label="Horizontal",
                        default=0.0,
                        maximum=100.0, decimals=1, step=0.5, suffix=" mm",
                    ),
                    Control(
                        type=ControlType.NUMBER,
                        target="layout.gutter_v_mm",
                        label="Vertical",
                        default=0.0,
                        maximum=100.0, decimals=1, step=0.5, suffix=" mm",
                        visible_when=_IS_NUP,
                    ),
                ),
            ),
            Section(
                title="Page Range",
                entity="which source pages are imposed",
                controls=(
                    Control(
                        type=ControlType.TEXT,
                        target="layout.page_range",
                        label="Pages",
                        default="",
                        placeholder="e.g. 1-4,7,10-12  (all if empty)",
                        description="Order matters: 5,2 imposes page 5 first.",
                    ),
                ),
            ),
        ),
    ),
    Tab(
        name="Sheet",
        sections=(
            Section(
                title="Press Sheet",
                entity="the paper being printed",
                controls=(
                    Control(
                        type=ControlType.SELECT,
                        target="sheet.preset",
                        label="Size",
                        default="A3",
                        options=_PRESET_OPTIONS,
                    ),
                    Control(
                        type=ControlType.NUMBER,
                        target="sheet.custom_width_mm",
                        label="Width",
                        default=297.0,
                        minimum=1.0, maximum=5000.0, decimals=1, suffix=" mm",
                        visible_when=When(target="sheet.preset", equals="Custom"),
                    ),
                    Control(
                        type=ControlType.NUMBER,
                        target="sheet.custom_height_mm",
                        label="Height",
                        default=420.0,
                        minimum=1.0, maximum=5000.0, decimals=1, suffix=" mm",
                        visible_when=When(target="sheet.preset", equals="Custom"),
                    ),
                    Control(
                        type=ControlType.SEGMENTED,
                        target="sheet.orientation",
                        label="Orientation",
                        default=Orientation.LANDSCAPE,
                        options=_enum_options(Orientation),
                    ),
                ),
            ),
            Section(
                title="Margins",
                entity="the unprintable edge of the sheet",
                controls=(
                    Control(type=ControlType.NUMBER, target="sheet.margin_top_mm",
                            label="Top", default=5.0, maximum=500.0, decimals=1, suffix=" mm"),
                    Control(type=ControlType.NUMBER, target="sheet.margin_bottom_mm",
                            label="Bottom", default=5.0, maximum=500.0, decimals=1, suffix=" mm"),
                    Control(type=ControlType.NUMBER, target="sheet.margin_left_mm",
                            label="Left", default=5.0, maximum=500.0, decimals=1, suffix=" mm"),
                    Control(type=ControlType.NUMBER, target="sheet.margin_right_mm",
                            label="Right", default=5.0, maximum=500.0, decimals=1, suffix=" mm"),
                ),
            ),
        ),
    ),
    Tab(
        name="Marks",
        sections=(
            Section(
                title="Printer Marks",
                entity="what gets drawn around the pages",
                controls=(
                    Control(
                        type=ControlType.COLLECTION,
                        target="marks",
                        label="Marks",
                    ),
                ),
            ),
        ),
    ),
)


# ── helpers ──────────────────────────────────────────

def all_controls() -> Tuple[Control, ...]:
    return tuple(c for tab in SCHEMA for s in tab.sections for c in s.controls)


def all_sections() -> Tuple[Section, ...]:
    return tuple(s for tab in SCHEMA for s in tab.sections)


def all_targets() -> Tuple[str, ...]:
    return tuple(c.target for c in all_controls())


def defaults() -> dict:
    """Every control's default, keyed by target."""
    return {c.target: c.default for c in all_controls()
            if c.type is not ControlType.COLLECTION}


def is_visible(control_or_section, values: dict) -> bool:
    """Whether a control/section applies, given the current values."""
    cond = control_or_section.visible_when
    if cond is None:
        return True
    return cond.holds(values.get(cond.target))


def is_length(control: Control) -> bool:
    """
    Whether a control edits a physical length, and so follows the display unit.

    The model is millimetres everywhere, so a millimetre suffix is exactly the
    marker: these are the fields that get shown in cm/in/pt when asked.
    """
    return control.type is ControlType.NUMBER and control.suffix.strip() == "mm"
