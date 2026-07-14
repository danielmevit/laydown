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
#  Source pages
# ──────────────────────────────────────────────

class SourceBox(Enum):
    """Which box of a source page gets imposed."""
    MEDIA = "Media Box"
    CROP = "Crop Box"
    TRIM = "Trim Box"
    BLEED = "Bleed Box"


@dataclass
class SourceSettings:
    """
    How to read the incoming pages.

    ``box`` is the area fitted to each cell — the TrimBox by default, because that
    is the finished page a press-ready PDF describes. PDF defines TrimBox to fall
    back to the CropBox and then the MediaBox, so this is also correct for plain
    PDFs that carry no boxes at all.

    ``bleed_mm`` pulls extra artwork beyond that box and lets it spill outside the
    cell, so an imprecise cut still lands on ink.
    """
    box: SourceBox = SourceBox.TRIM
    bleed_mm: float = 0.0


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


class BookletMode(Enum):
    """
    How the folded sheets are assembled into the finished book.

    SADDLE_STITCH nests every sheet inside the next and staples through the fold,
    so the whole document is one signature. PERFECT_BOUND splits it into signatures
    of ``signature_sheets`` sheets which are folded separately and *gathered* —
    stacked spine-to-spine and glued — which is why the page order differs.
    """
    SADDLE_STITCH = "Saddle Stitch"
    PERFECT_BOUND = "Perfect Bound"


@dataclass
class LayoutSettings:
    layout_type: LayoutType = LayoutType.NUP

    # N-Up. rows/cols override nup when both are set.
    nup: int = 2  # 2, 4
    rows: int = 0
    cols: int = 0
    auto_rotate: bool = False  # turn a page 90° when that fits its cell better

    # Booklet
    booklet_mode: BookletMode = BookletMode.SADDLE_STITCH
    signature_sheets: int = 4  # sheets per signature; perfect-bound only
    right_to_left: bool = False
    fillers_in_middle: bool = False  # pad in the centre instead of at the end

    # Gutters
    gutter_h_mm: float = 0.0
    gutter_v_mm: float = 0.0

    # Page range (empty = all)
    page_range: str = ""

    # Page creep — compensation for the fore-edge push-out of a folded signature.
    # Both values are a shift *towards the spine*, interpolated across the nest by
    # sheet depth; negatives shift away from it. Stated as explicit endpoints rather
    # than derived from paper caliper, so the operator's measurement wins.
    creep_enabled: bool = False
    creep_outer_mm: float = 0.0  # outermost sheet, normally 0
    creep_inner_mm: float = 0.0  # innermost sheet, the one that creeps most


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
    GAP_CROP_MARKS = "Gap Crop Marks"
    TRIM_LINE = "Trim Line"
    REGISTRATION = "Registration Marks"
    FOLDING_MARKS = "Folding Marks"
    PERFORATION_MARKS = "Perforation Marks"
    COLLATING_MARKS = "Collating Marks"
    COLOR_BAR = "Colour Bar"
    TEXT_LABEL = "Text Label"
    CUSTOM_MARK = "Custom Mark (PDF)"


@dataclass
class MarkItem:
    mark_type: MarkType
    enabled: bool = True

    # Crop / gap crop marks
    crop_length_mm: float = 5.0
    crop_offset_mm: float = 3.0
    crop_width_pt: float = 0.5

    # Text label
    label_text: str = ""  # empty = auto (filename + sheet info)
    label_font_size: int = 8

    # Folding / perforation marks
    fold_line_length_mm: float = 10.0

    # Colour bar
    patch_size_mm: float = 5.0

    # Custom mark: any PDF, stamped onto the sheet. Imposition Wizard ships
    # placeholder PDFs for its bull's-eyes and colour bars, which gives the game
    # away — a custom mark is just artwork placed by rule, and show_pdf_page
    # already does that for us, vector and all.
    mark_pdf_path: str = ""
    mark_width_mm: float = 20.0
    mark_x_mm: float = 10.0
    mark_y_mm: float = 10.0


# ──────────────────────────────────────────────
#  Project (top-level container)
# ──────────────────────────────────────────────

@dataclass
class Project:
    """Top-level container holding every setting the engine reads."""
    source: SourceSettings = field(default_factory=SourceSettings)
    preprocessors: List[PreprocessorStep] = field(default_factory=list)
    layout: LayoutSettings = field(default_factory=LayoutSettings)
    sheet: SheetSettings = field(default_factory=SheetSettings)
    marks: List[MarkItem] = field(default_factory=list)
    source_pdf_path: str = ""
