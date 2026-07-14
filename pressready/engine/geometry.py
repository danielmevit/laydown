"""
Placement geometry — the single answer to "what goes where on which sheet".

Both the imposition engine and the preview overlay need this. They used to work it
out separately, which meant the magenta overlay could quietly disagree with the
printed result; everything now plans through :func:`sheet_plan`.

Two rects matter for every placed page and they are not the same:

* **place box** — the box that is fitted to the cell. Normally the TrimBox: the
  finished, cut page. This is what crop marks must mark.
* **clip box** — the area actually drawn, which is the place box plus any bleed.
  It deliberately spills outside the cell so a slightly-off cut still hits ink.

All rects are PDF points in PyMuPDF's top-left coordinate space.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

import fitz

from pressready.engine.data_model import (
    BookletMode,
    LayoutSettings,
    LayoutType,
    Project,
    SourceBox,
    SourceSettings,
)
from pressready.engine.utils import mm_to_pt


# ── sheet-level geometry ─────────────────────────────

def sheet_size_pt(project: Project) -> Tuple[float, float]:
    """(width, height) of the press sheet in points."""
    w_mm, h_mm = project.sheet.sheet_size_mm()
    return mm_to_pt(w_mm), mm_to_pt(h_mm)


def margins_pt(project: Project) -> Tuple[float, float, float, float]:
    """(left, right, top, bottom) margins in points."""
    s = project.sheet
    return (
        mm_to_pt(s.margin_left_mm),
        mm_to_pt(s.margin_right_mm),
        mm_to_pt(s.margin_top_mm),
        mm_to_pt(s.margin_bottom_mm),
    )


# Convenience grids for the plain "N pages per sheet" choice. Anything not listed
# here is expressed by setting rows/cols directly.
_NUP_GRIDS = {1: (1, 1), 2: (2, 1), 4: (2, 2), 6: (3, 2), 8: (4, 2), 9: (3, 3), 16: (4, 4)}


def grid_for(layout) -> Tuple[int, int]:
    """(cols, rows) for an N-Up layout."""
    if layout.rows and layout.cols:
        if layout.rows < 1 or layout.cols < 1:
            raise ValueError(
                f"rows and cols must be at least 1, got {layout.rows}×{layout.cols}")
        return layout.cols, layout.rows
    try:
        return _NUP_GRIDS[layout.nup]
    except KeyError:
        raise ValueError(
            f"nup must be one of {sorted(_NUP_GRIDS)} (or set rows/cols explicitly), "
            f"got {layout.nup}"
        ) from None


def cell_grid(project: Project, cols: int, rows: int) -> List[fitz.Rect]:
    """The cols×rows cells of a sheet, in reading order."""
    sheet_w, sheet_h = sheet_size_pt(project)
    ml, mr, mt, mb = margins_pt(project)
    gh = mm_to_pt(project.layout.gutter_h_mm)
    gv = mm_to_pt(project.layout.gutter_v_mm)

    cell_w = (sheet_w - ml - mr - (cols - 1) * gh) / cols
    cell_h = (sheet_h - mt - mb - (rows - 1) * gv) / rows
    if cell_w <= 0 or cell_h <= 0:
        raise ValueError("Margins/gutters too large for sheet size")

    cells = []
    for i in range(cols * rows):
        col, row = i % cols, i // cols
        x0 = ml + col * (cell_w + gh)
        y0 = mt + row * (cell_h + gv)
        cells.append(fitz.Rect(x0, y0, x0 + cell_w, y0 + cell_h))
    return cells


# ── source boxes ─────────────────────────────────────

def _raw_box(page: fitz.Page, which: SourceBox) -> fitz.Rect:
    if which == SourceBox.MEDIA:
        return page.mediabox
    if which == SourceBox.CROP:
        return page.cropbox
    if which == SourceBox.BLEED:
        return page.bleedbox
    return page.trimbox


def source_boxes(page: fitz.Page, source: SourceSettings) -> Tuple[fitz.Rect, fitz.Rect]:
    """
    Return (place_box, clip_box) for *page*.

    PDF defines TrimBox/BleedBox to default to the CropBox, and PyMuPDF honours that,
    so asking for the TrimBox of a plain PDF that has none simply yields the whole
    page — which is why TrimBox is a safe default rather than a risky one.
    """
    box = _raw_box(page, source.box) & page.rect
    if box.is_empty:
        box = fitz.Rect(page.rect)

    if source.bleed_mm <= 0:
        return box, box

    b = mm_to_pt(source.bleed_mm)
    clip = fitz.Rect(box.x0 - b, box.y0 - b, box.x1 + b, box.y1 + b) & page.rect
    if clip.is_empty:
        return box, box
    return box, clip


# ── fitting a page into a cell ───────────────────────

def fitted_rect(cell: fitz.Rect, width: float, height: float) -> fitz.Rect:
    """Where a width×height box lands inside *cell*, fitted and centred."""
    scale = min(cell.width / width, cell.height / height)
    w, h = width * scale, height * scale
    x0 = cell.x0 + (cell.width - w) / 2
    y0 = cell.y0 + (cell.height - h) / 2
    return fitz.Rect(x0, y0, x0 + w, y0 + h)


def place_page(
    cell: fitz.Rect,
    place: fitz.Rect,
    clip: fitz.Rect,
    allow_rotate: bool = False,
) -> Tuple[fitz.Rect, fitz.Rect, int]:
    """
    Work out where to draw so that *place* lands exactly on the cell.

    Returns (target, trim, rotate):

    * *target* — the rect to hand ``show_pdf_page``. It is sized for the clip, so
      bleed deliberately spills outside the cell.
    * *trim* — where the place box ends up on the sheet. This is what crop marks
      must follow: a page whose proportions don't match its cell is letterboxed
      inside it, and marking the cell instead is how you get crop marks that miss
      the paper.
    * *rotate* — 0 or 90. With *allow_rotate*, a page is turned a quarter turn when
      that fills its cell better, which is what lets landscape artwork sit on a
      portrait sheet without the operator pre-rotating the file.
    """
    rotate = 0
    if allow_rotate:
        upright = min(cell.width / place.width, cell.height / place.height)
        turned = min(cell.width / place.height, cell.height / place.width)
        if turned > upright:
            rotate = 90

    pw, ph = (place.width, place.height) if rotate == 0 else (place.height, place.width)
    trim = fitted_rect(cell, pw, ph)
    if clip == place:
        return trim, trim, rotate

    scale = trim.width / pw
    # Bleed margins around the place box, in source space.
    left, top = place.x0 - clip.x0, place.y0 - clip.y0
    right, bottom = clip.x1 - place.x1, clip.y1 - place.y1
    if rotate == 90:
        # show_pdf_page's quarter turn sends the source's top edge to the left of the
        # sheet and its right edge to the top (verified against output, not assumed),
        # so the bleed margins travel with it.
        left, top, right, bottom = top, right, bottom, left

    target = fitz.Rect(
        trim.x0 - left * scale, trim.y0 - top * scale,
        trim.x1 + right * scale, trim.y1 + bottom * scale,
    )
    return target, trim, rotate


def target_rect(cell: fitz.Rect, place: fitz.Rect, clip: fitz.Rect) -> Tuple[fitz.Rect, fitz.Rect]:
    """(target, trim) without rotation. Thin wrapper kept for callers that never turn pages."""
    target, trim, _ = place_page(cell, place, clip, allow_rotate=False)
    return target, trim


# ── page ordering ────────────────────────────────────

def _saddle_positions(m: int) -> List[Tuple[int, int]]:
    """
    Nesting order for *m* slots (a multiple of 4), as (left, right) slot positions.

    Facing slots always sum to m-1 — that is what makes a folded signature read in
    order once it is nested and stapled through the fold.
    """
    result = []
    lo, hi = 0, m - 1
    while lo < hi:
        result.append((hi, lo))
        lo += 1
        hi -= 1
        result.append((lo, hi))
        lo += 1
        hi -= 1
    return result


def padded_slots(n: int, fillers_in_middle: bool = False) -> List[int]:
    """
    Page slots for a booklet of *n* pages, padded to a multiple of four with -1.

    A folded sheet always carries four pages, so a booklet's length is rounded up.
    By default the blanks land at the end (a blank back cover). fillers_in_middle
    puts them in the centre instead, which keeps the back cover printed.
    """
    padded = ((n + 3) // 4) * 4
    blanks = padded - n
    slots = list(range(n))
    if not blanks:
        return slots
    if fillers_in_middle:
        mid = n // 2
        return slots[:mid] + [-1] * blanks + slots[mid:]
    return slots + [-1] * blanks


def signature_groups(n: int, layout) -> List[List[int]]:
    """
    Split the padded slots into signatures — the units that get folded together.

    Saddle stitch nests the whole document as one signature. Perfect binding folds
    fixed-size signatures separately and gathers them, so each is nested on its own.
    """
    slots = padded_slots(n, layout.fillers_in_middle)
    if layout.booklet_mode != BookletMode.PERFECT_BOUND:
        return [slots]

    sheets = max(1, int(layout.signature_sheets or 1))
    per_signature = sheets * 4
    groups = [slots[i:i + per_signature] for i in range(0, len(slots), per_signature)]
    for group in groups:
        while len(group) % 4:
            group.append(-1)
    return groups


def booklet_page_order(
    n: int,
    layout=None,
) -> List[Tuple[int, int]]:
    """
    Booklet page ordering: (left, right) page indices per printed side; -1 = blank.

    With no *layout* this is a plain saddle stitch, which is what the simple
    invariants (every page once, facing pages sum to a constant) are checked against.
    """
    if layout is None:
        layout = LayoutSettings(layout_type=LayoutType.BOOKLET)

    order: List[Tuple[int, int]] = []
    for group in signature_groups(n, layout):
        for a, b in _saddle_positions(len(group)):
            left, right = group[a], group[b]
            if layout.right_to_left:
                left, right = right, left
            order.append((left, right))
    return order


def creep_shift_pt(layout, depth: int, sheets_in_signature: int) -> float:
    """
    How far this sheet's pages move towards the spine, in points.

    Nested sheets push out at the fore-edge, and trimming the folded stack flush
    takes more off the inner leaves. Compensation walks linearly from the outermost
    sheet's shift to the innermost one's.
    """
    if not layout.creep_enabled:
        return 0.0
    if sheets_in_signature <= 1:
        return mm_to_pt(layout.creep_inner_mm)
    t = depth / (sheets_in_signature - 1)
    return mm_to_pt(layout.creep_outer_mm + (layout.creep_inner_mm - layout.creep_outer_mm) * t)


# ── the plan ─────────────────────────────────────────

@dataclass(frozen=True)
class Placement:
    """One source page in one cell of one sheet."""
    cell: fitz.Rect
    page_index: int  # index into the source document; -1 = deliberately blank


@dataclass(frozen=True)
class Sheet:
    """One printed side of the output."""
    placements: List[Placement]
    number: int                      # physical sheet, 1-based
    total: int                       # physical sheets in the job
    side: str = ""                   # "", "Front" or "Back"
    fold_x: Optional[float] = None   # x of the fold line, booklet only

    @property
    def cells(self) -> List[fitz.Rect]:
        return [p.cell for p in self.placements]


def sheet_plan(project: Project, page_indices: List[int]) -> List[Sheet]:
    """
    Plan the whole job: which source page goes in which cell of which sheet.

    The one place layout decisions are made. The imposition engine renders this
    plan; the preview draws its overlays from the same plan, so they cannot drift.
    """
    if project.layout.layout_type == LayoutType.BOOKLET:
        return _plan_booklet(project, page_indices)
    return _plan_nup(project, page_indices)


def _plan_nup(project: Project, page_indices: List[int]) -> List[Sheet]:
    cols, rows = grid_for(project.layout)
    cells = cell_grid(project, cols, rows)
    per_sheet = cols * rows

    n = len(page_indices)
    num_sheets = max(1, (n + per_sheet - 1) // per_sheet)

    sheets = []
    for si in range(num_sheets):
        placements = []
        for ci in range(per_sheet):
            idx = si * per_sheet + ci
            if idx >= n:
                break
            placements.append(Placement(cells[ci], page_indices[idx]))
        sheets.append(Sheet(placements=placements, number=si + 1, total=num_sheets))
    return sheets


def _shifted(cell: fitz.Rect, dx: float) -> fitz.Rect:
    return fitz.Rect(cell.x0 + dx, cell.y0, cell.x1 + dx, cell.y1)


def _plan_booklet(project: Project, page_indices: List[int]) -> List[Sheet]:
    layout = project.layout
    cells = cell_grid(project, 2, 1)
    gh = mm_to_pt(layout.gutter_h_mm)
    fold_x = cells[0].x1 + gh / 2 if gh else cells[0].x1

    groups = signature_groups(len(page_indices), layout)
    total_sheets = sum(len(_saddle_positions(len(g))) // 2 for g in groups)

    sheets: List[Sheet] = []
    sheet_no = 0
    for group in groups:
        positions = _saddle_positions(len(group))
        sheets_in_signature = len(positions) // 2

        for si, (a, b) in enumerate(positions):
            depth = si // 2  # 0 = outermost sheet of this signature
            if si % 2 == 0:
                sheet_no += 1

            # Creep moves each page towards the spine, which is the fold between the
            # two cells: the left page moves right, the right page moves left.
            shift = creep_shift_pt(layout, depth, sheets_in_signature)
            left_cell = _shifted(cells[0], shift)
            right_cell = _shifted(cells[1], -shift)

            left, right = group[a], group[b]
            if layout.right_to_left:
                left, right = right, left

            placements = []
            if left >= 0:
                placements.append(Placement(left_cell, page_indices[left]))
            if right >= 0:
                placements.append(Placement(right_cell, page_indices[right]))

            sheets.append(Sheet(
                placements=placements,
                number=sheet_no,
                total=total_sheets,
                side="Front" if si % 2 == 0 else "Back",
                fold_x=fold_x,
            ))
    return sheets
