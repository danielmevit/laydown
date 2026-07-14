"""
Imposition engine — N-Up and Booklet layout generation.

Uses PyMuPDF show_pdf_page for vector-quality placement (zero rasterization).
Supports: N-Up (2/4), Booklet (saddle-stitch), gutters, marks pipeline.
"""

import os
import tempfile
from typing import List, Optional, Tuple, Callable

import fitz

from pressready.engine.utils import mm_to_pt, parse_page_range
from pressready.engine.data_model import (
    Project,
    LayoutType,
    MarkItem,
    SHEET_PRESETS_MM,
)
from pressready.engine.preprocessors import apply_preprocessors
from pressready.engine.marks import draw_marks


def _get_sheet_dims_pt(project: Project) -> Tuple[float, float]:
    """Return (width, height) in points from project sheet settings."""
    w_mm, h_mm = project.sheet.sheet_size_mm()
    return mm_to_pt(w_mm), mm_to_pt(h_mm)


def _margins_pt(project: Project) -> Tuple[float, float, float, float]:
    """Return (left, right, top, bottom) margins in points."""
    s = project.sheet
    return (
        mm_to_pt(s.margin_left_mm),
        mm_to_pt(s.margin_right_mm),
        mm_to_pt(s.margin_top_mm),
        mm_to_pt(s.margin_bottom_mm),
    )


# ──────────────────────────────────────────────────────
#  Imposition entry point
# ──────────────────────────────────────────────────────


def impose(
    project: Project,
    output_path: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> int:
    """
    Run the full pipeline: preprocess → impose → marks → save.

    Returns the number of output pages (sides) written.
    """
    if not project.source_pdf_path:
        raise ValueError("No source PDF set")

    src_doc = fitz.open(project.source_pdf_path)
    try:
        if len(src_doc) == 0:
            raise ValueError("Source PDF has no pages")

        # --- Preprocessors ---
        # May hand back a different document (see apply_preprocessors' contract).
        work_doc = apply_preprocessors(src_doc, project.preprocessors)
        try:
            # --- Page selection ---
            total = len(work_doc)
            expr = project.layout.page_range.strip()
            if expr:
                page_indices = parse_page_range(expr, total)
            else:
                page_indices = list(range(total))

            # --- Impose ---
            if project.layout.layout_type == LayoutType.BOOKLET:
                return _impose_booklet(
                    project, work_doc, page_indices, output_path, progress_callback)
            return _impose_nup(
                project, work_doc, page_indices, output_path, progress_callback)
        finally:
            if work_doc is not src_doc:
                work_doc.close()
    finally:
        src_doc.close()


def impose_to_temp(
    project: Project,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Tuple[str, int]:
    """
    Impose to a temporary file and return (tmp_path, num_pages).

    Caller is responsible for deleting the temp file.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp_path = tmp.name
    tmp.close()
    try:
        n = impose(project, tmp_path, progress_callback)
        return tmp_path, n
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ──────────────────────────────────────────────────────
#  N-Up
# ──────────────────────────────────────────────────────


def _impose_nup(
    project: Project,
    src_doc: fitz.Document,
    page_indices: List[int],
    output_path: str,
    progress_callback: Optional[Callable],
) -> int:
    nup = project.layout.nup
    if nup not in (2, 4):
        raise ValueError(f"nup must be 2 or 4, got {nup}")

    cols = 2
    rows = 1 if nup == 2 else 2

    sheet_w, sheet_h = _get_sheet_dims_pt(project)
    ml, mr, mt, mb = _margins_pt(project)
    gh = mm_to_pt(project.layout.gutter_h_mm)
    gv = mm_to_pt(project.layout.gutter_v_mm)

    avail_w = sheet_w - ml - mr - (cols - 1) * gh
    avail_h = sheet_h - mt - mb - (rows - 1) * gv
    cell_w = avail_w / cols
    cell_h = avail_h / rows

    if cell_w <= 0 or cell_h <= 0:
        raise ValueError("Margins/gutters too large for sheet size")

    num_src = len(page_indices)
    num_sheets = (num_src + nup - 1) // nup
    out_doc = fitz.open()

    preset_label = project.sheet.preset
    filename = os.path.basename(project.source_pdf_path)

    try:
        for si in range(num_sheets):
            if progress_callback:
                progress_callback(si, num_sheets)

            page = out_doc.new_page(width=sheet_w, height=sheet_h)
            cell_rects: List[fitz.Rect] = []

            for ci in range(nup):
                idx = si * nup + ci
                if idx >= num_src:
                    break
                col = ci % cols
                row = ci // cols
                x0 = ml + col * (cell_w + gh)
                y0 = mt + row * (cell_h + gv)
                rect = fitz.Rect(x0, y0, x0 + cell_w, y0 + cell_h)
                page.show_pdf_page(
                    rect, src_doc, page_indices[idx], keep_proportion=True, overlay=True)
                cell_rects.append(rect)

            draw_marks(
                page, project.marks, cell_rects,
                sheet_w, sheet_h, ml, mr, mt, mb,
                sheet_num=si + 1, total_sheets=num_sheets,
                filename=filename,
                layout_info=f"{nup}-Up on {preset_label}",
            )

        if progress_callback:
            progress_callback(num_sheets, num_sheets)

        out_doc.save(output_path, garbage=4, deflate=True)
    finally:
        out_doc.close()
    return num_sheets


# ──────────────────────────────────────────────────────
#  Booklet (saddle-stitch)
# ──────────────────────────────────────────────────────


def booklet_page_order(n: int) -> List[Tuple[int, int]]:
    """
    Saddle-stitch page ordering.

    Returns list of (left_page, right_page) tuples, 0-based.
    -1 means blank.
    """
    padded = ((n + 3) // 4) * 4
    result = []
    lo, hi = 0, padded - 1
    while lo < hi:
        result.append((hi, lo))
        lo += 1
        hi -= 1
        result.append((lo, hi))
        lo += 1
        hi -= 1
    return [
        (l if l < n else -1, r if r < n else -1)
        for l, r in result
    ]


def _impose_booklet(
    project: Project,
    src_doc: fitz.Document,
    page_indices: List[int],
    output_path: str,
    progress_callback: Optional[Callable],
) -> int:
    sheet_w, sheet_h = _get_sheet_dims_pt(project)
    ml, mr, mt, mb = _margins_pt(project)
    gh = mm_to_pt(project.layout.gutter_h_mm)

    cols, rows = 2, 1
    avail_w = sheet_w - ml - mr - gh
    avail_h = sheet_h - mt - mb
    cell_w = avail_w / cols
    cell_h = avail_h / rows

    if cell_w <= 0 or cell_h <= 0:
        raise ValueError("Margins/gutters too large for sheet size")

    num_src = len(page_indices)
    order = booklet_page_order(num_src)
    num_sides = len(order)
    num_sheets = num_sides // 2
    out_doc = fitz.open()

    preset_label = project.sheet.preset
    filename = os.path.basename(project.source_pdf_path)
    fold_x = ml + cell_w + gh / 2

    try:
        for si, (lp, rp) in enumerate(order):
            if progress_callback:
                progress_callback(si, num_sides)

            page = out_doc.new_page(width=sheet_w, height=sheet_h)
            cell_rects: List[fitz.Rect] = []

            if lp >= 0:
                r = fitz.Rect(ml, mt, ml + cell_w, mt + cell_h)
                page.show_pdf_page(
                    r, src_doc, page_indices[lp], keep_proportion=True, overlay=True)
                cell_rects.append(r)

            if rp >= 0:
                rx0 = ml + cell_w + gh
                r = fitz.Rect(rx0, mt, rx0 + cell_w, mt + cell_h)
                page.show_pdf_page(
                    r, src_doc, page_indices[rp], keep_proportion=True, overlay=True)
                cell_rects.append(r)

            # Two sides make one physical sheet: marks that count or step must
            # count sheets, not sides, or a 4-side booklet claims to be 4 sheets.
            sheet_num = si // 2 + 1
            side = "Front" if si % 2 == 0 else "Back"
            draw_marks(
                page, project.marks, cell_rects,
                sheet_w, sheet_h, ml, mr, mt, mb,
                sheet_num=sheet_num, total_sheets=num_sheets,
                filename=filename,
                layout_info=f"Booklet on {preset_label} — {side}",
                fold_x=fold_x,
            )

        if progress_callback:
            progress_callback(num_sides, num_sides)

        out_doc.save(output_path, garbage=4, deflate=True)
    finally:
        out_doc.close()
    return num_sides
