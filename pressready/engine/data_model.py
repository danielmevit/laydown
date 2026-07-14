"""
Data model for PressReady v2.

All settings for the 4-tab workflow: Preprocessors, Layout, Sheet, Marks.
Used as the shared contract between engine and UI.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum


# ──────────────────────────────────────────────
#  Sheet size presets (portrait: width < height)
# ──────────────────────────────────────────────

SHEET_PRESETS_MM = {
    "A5": (148.0, 210.0),
    "A4": (210.0, 297.0),
    "A3": (297.0, 420.0),
    "A2": (420.0, 594.0),
    "Letter": (215.9, 279.4),
    "Legal": (215.9, 355.6),
    "Tabloid": (279.4, 431.8),
}


# ──────────────────────────────────────────────
#  Preprocessors
# ──────────────────────────────────────────────

class PreprocessorType(Enum):
    ROTATE_PAGES = "Rotate Pages"
    SCALE_PAGES = "Scale Pages"
    REORDER_PAGES = "Reorder Pages"
    CLONE_PAGES = "Clone Pages"
    N_PLUS_1_PAGES = "N + 1 Pages"
    SPLIT_PAGES = "Split Pages"
    SHUFFLE_PAGES = "Shuffle Pages"
    RESIZE_PAGES = "Resize Pages"
    OVERRIDE_BOX = "Override Box"
    SETUP_BLEEDS = "Setup Bleeds"
    CENTER_AND_CROP = "Center and Crop"
    SLICE_PAGES = "Slice Pages"


class RotateAngle(Enum):
    CW_90 = 90
    CW_180 = 180
    CW_270 = 270


@dataclass
class PreprocessorStep:
    type: PreprocessorType
    enabled: bool = True

    # Rotate
    rotate_angle: RotateAngle = RotateAngle.CW_90

    # Scale
    scale_factor: float = 1.0  # 1.0 = 100 %

    # Reorder
    page_order: str = ""  # e.g. "4,3,2,1" or "reverse"


# ──────────────────────────────────────────────
#  Layout
# ──────────────────────────────────────────────

class LayoutType(Enum):
    NUP = "N-Up"
    BOOKLET = "Booklet"


class BookletType(Enum):
    TWO_UP = "2-up"


class BookletMode(Enum):
    SHEETWISE = "Sheetwise"
    WORK_AND_TURN = "Work and Turn"
    WORK_AND_TUMBLE = "Work and Tumble"
    PERFECT_BOUND = "Perfect Bound"


class CreepMode(Enum):
    SHIFT_BOTH = "Shift (move both edges)"
    SHIFT_IN = "Shift In"
    SHIFT_OUT = "Shift Out"
    SCALE = "Scale"


@dataclass
class LayoutSettings:
    layout_type: LayoutType = LayoutType.NUP

    # N-Up
    nup: int = 2  # 2, 4

    # Booklet
    booklet_type: BookletType = BookletType.TWO_UP
    booklet_mode: BookletMode = BookletMode.SHEETWISE
    right_to_left: bool = False
    move_fillers_to_middle: bool = False

    # Gutters
    gutter_h_mm: float = 0.0
    gutter_v_mm: float = 0.0

    # Page range (empty = all)
    page_range: str = ""

    # Signatures
    signatures_enabled: bool = False
    signature_size: int = 1  # sheets per signature

    # Folding
    fold_in_parts: bool = False
    fold_part_size: int = 1

    # Page Creep
    creep_enabled: bool = False
    creep_mode: CreepMode = CreepMode.SHIFT_BOTH
    creep_outer_mm: float = 0.0
    creep_inner_mm: float = 0.0


# ──────────────────────────────────────────────
#  Sheet
# ──────────────────────────────────────────────

class Orientation(Enum):
    LANDSCAPE = "Landscape"
    PORTRAIT = "Portrait"


@dataclass
class SheetSettings:
    preset: str = "A3"  # key in SHEET_PRESETS_MM, or "Custom"
    custom_width_mm: float = 297.0
    custom_height_mm: float = 420.0
    orientation: Orientation = Orientation.LANDSCAPE

    margin_top_mm: float = 5.0
    margin_bottom_mm: float = 5.0
    margin_left_mm: float = 5.0
    margin_right_mm: float = 5.0

    def sheet_size_mm(self) -> Tuple[float, float]:
        """Return (w, h) in mm after applying orientation."""
        if self.preset == "Custom":
            w, h = self.custom_width_mm, self.custom_height_mm
        else:
            w, h = SHEET_PRESETS_MM.get(self.preset, (297.0, 420.0))
        if self.orientation == Orientation.LANDSCAPE:
            return (max(w, h), min(w, h))
        return (min(w, h), max(w, h))


# ──────────────────────────────────────────────
#  Marks
# ──────────────────────────────────────────────

class MarkType(Enum):
    CROP_MARKS = "Crop Marks"
    TRIM_LINE = "Trim Line"
    REGISTRATION = "Registration Marks"
    FOLDING_MARKS = "Folding Marks"
    TEXT_LABEL = "Text Label"
    COLLATING_MARKS = "Collating Marks"


@dataclass
class MarkItem:
    mark_type: MarkType
    enabled: bool = True

    # Crop marks
    crop_length_mm: float = 5.0
    crop_offset_mm: float = 3.0
    crop_width_pt: float = 0.5

    # Text label
    label_text: str = ""  # empty = auto (filename + sheet info)
    label_font_size: int = 8

    # Folding marks
    fold_line_length_mm: float = 10.0


# ──────────────────────────────────────────────
#  Project (top-level container)
# ──────────────────────────────────────────────

@dataclass
class Project:
    """Top-level container holding all 4 tabs of settings."""
    preprocessors: List[PreprocessorStep] = field(default_factory=list)
    layout: LayoutSettings = field(default_factory=LayoutSettings)
    sheet: SheetSettings = field(default_factory=SheetSettings)
    marks: List[MarkItem] = field(default_factory=list)
    source_pdf_path: str = ""
