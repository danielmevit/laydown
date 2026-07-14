"""
Bench-harness helpers — the ground-truth machinery shared by the tests.

The idea (see ROADMAP.md Phase 1): build a source PDF whose pages carry findable
text tokens at known places, impose it, then read the tokens back out of the
*output* and check they landed where the geometry says they should.

Nothing here hardcodes font metrics. Expected positions are derived by reading a
token's box out of the source page and pushing it through the same fit-and-centre
transform ``show_pdf_page`` applies, so the assertion is about placement only.
"""

from typing import Dict, Optional, Tuple

import fitz

from pressready.engine.utils import mm_to_pt


# ── tokens ───────────────────────────────────────────

def page_token(n: int) -> str:
    """Centre token identifying source page *n* (1-based)."""
    return f"PG{n:03d}"


def corner_token(n: int, corner: str) -> str:
    """Corner token for source page *n*. corner in {TL, TR, BL, BR}."""
    return f"{corner}{n:03d}"


SLUG_TOKEN = "SLUGMARK"


# ── source PDF builder ───────────────────────────────

def make_source_pdf(
    path: str,
    n_pages: int = 4,
    w_mm: float = 210.0,
    h_mm: float = 297.0,
    trim_inset_mm: float = 0.0,
    bleed_mm: float = 0.0,
    slug: bool = False,
) -> str:
    """
    Write a synthetic source PDF and return *path*.

    Every page gets a centre token (``PG001``…) and four corner tokens placed just
    inside the **trim box**, so a placement check can identify both which page
    landed where and how its box was mapped.

    trim_inset_mm > 0 insets the trim box from the media box, and bleed_mm grows a
    bleed box outwards from the trim box — the shape a real press-ready PDF has.
    slug=True writes a token out in the media margin, outside any bleed: it must
    survive a media-box imposition and be clipped away by a trim-box one.
    """
    doc = fitz.open()
    w, h = mm_to_pt(w_mm), mm_to_pt(h_mm)
    inset = mm_to_pt(trim_inset_mm)
    bleed = mm_to_pt(bleed_mm)

    for i in range(1, n_pages + 1):
        page = doc.new_page(width=w, height=h)
        trim = fitz.Rect(inset, inset, w - inset, h - inset)

        # Ink across the whole bleed area so a bleed placement has something to show.
        if bleed > 0:
            page.draw_rect(
                fitz.Rect(trim.x0 - bleed, trim.y0 - bleed, trim.x1 + bleed, trim.y1 + bleed),
                color=None, fill=(0.85, 0.9, 1.0),
            )
        page.draw_rect(trim, color=(0.2, 0.2, 0.2), width=0.5)

        pad = 6.0
        page.insert_text((trim.x0 + pad, trim.y0 + pad + 8), corner_token(i, "TL"), fontsize=8)
        page.insert_text((trim.x1 - pad - 34, trim.y0 + pad + 8), corner_token(i, "TR"), fontsize=8)
        page.insert_text((trim.x0 + pad, trim.y1 - pad), corner_token(i, "BL"), fontsize=8)
        page.insert_text((trim.x1 - pad - 34, trim.y1 - pad), corner_token(i, "BR"), fontsize=8)
        page.insert_text(
            ((trim.x0 + trim.x1) / 2 - 20, (trim.y0 + trim.y1) / 2),
            page_token(i), fontsize=14,
        )

        if slug and inset > 0:
            page.insert_text((2, 10), SLUG_TOKEN, fontsize=6)

        if inset > 0:
            page.set_trimbox(trim)
        if bleed > 0:
            page.set_bleedbox(
                fitz.Rect(trim.x0 - bleed, trim.y0 - bleed, trim.x1 + bleed, trim.y1 + bleed)
            )

    doc.save(path)
    doc.close()
    return path


# ── reading tokens back ──────────────────────────────

def word_boxes(page: fitz.Page) -> Dict[str, fitz.Rect]:
    """Map every extracted word on *page* to its bounding box."""
    out: Dict[str, fitz.Rect] = {}
    for x0, y0, x1, y1, word, *_ in page.get_text("words"):
        out[word] = fitz.Rect(x0, y0, x1, y1)
    return out


def word_centers(page: fitz.Page) -> Dict[str, fitz.Point]:
    """Map every extracted word on *page* to the centre of its bounding box."""
    return {w: fitz.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)
            for w, r in word_boxes(page).items()}


# ── the placement transform, re-derived independently ─

def fitted_rect(cell: fitz.Rect, src_w: float, src_h: float) -> fitz.Rect:
    """
    Where a src_w × src_h box lands inside *cell* under keep_proportion=True.

    Re-derived here on purpose: the test must not import the engine's own maths,
    or it would agree with the engine's bugs.
    """
    scale = min(cell.width / src_w, cell.height / src_h)
    w, h = src_w * scale, src_h * scale
    x0 = cell.x0 + (cell.width - w) / 2
    y0 = cell.y0 + (cell.height - h) / 2
    return fitz.Rect(x0, y0, x0 + w, y0 + h)


def project_point(p: fitz.Point, src_box: fitz.Rect, cell: fitz.Rect) -> fitz.Point:
    """Map *p* (in source-page coords) to output coords for a box placed in *cell*."""
    fit = fitted_rect(cell, src_box.width, src_box.height)
    scale = fit.width / src_box.width
    return fitz.Point(
        fit.x0 + (p.x - src_box.x0) * scale,
        fit.y0 + (p.y - src_box.y0) * scale,
    )


def assert_near(actual: fitz.Point, expected: fitz.Point, tol: float = 1.5, what: str = "") -> None:
    dx, dy = abs(actual.x - expected.x), abs(actual.y - expected.y)
    assert dx <= tol and dy <= tol, (
        f"{what}: expected ≈({expected.x:.2f}, {expected.y:.2f}), "
        f"got ({actual.x:.2f}, {actual.y:.2f}) — off by ({dx:.2f}, {dy:.2f}) pt"
    )
