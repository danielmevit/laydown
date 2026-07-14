"""
Preprocessor pipeline — transforms applied to source pages before imposition.

The pipeline is: source PDF → preprocess chain → impose engine.

Ownership: a step either mutates the document in place or returns a replacement.
``apply_preprocessors`` closes any intermediate *it* created, and returns the final
document. The caller still owns the document it passed in: if the returned document
is a different object, close both.
"""

from typing import List

import fitz

from pressready.engine.data_model import (
    PreprocessorStep,
    PreprocessorType,
    RotateAngle,
)


def apply_preprocessors(
    doc: fitz.Document,
    steps: List[PreprocessorStep],
) -> fitz.Document:
    """
    Apply a chain of preprocessor steps to *doc*.

    Raises ValueError if a step is configured with something that can't be applied —
    a preprocessor must never quietly do nothing.
    """
    current = doc
    ours = False  # whether `current` is an intermediate we must close on replacement

    try:
        for step in steps:
            if not step.enabled:
                continue
            if step.type == PreprocessorType.ROTATE_PAGES:
                _rotate(current, step.rotate_angle)
            elif step.type == PreprocessorType.SCALE_PAGES:
                replacement = _scale(current, step.scale_factor)
                if replacement is not current:
                    if ours:
                        current.close()
                    current, ours = replacement, True
            elif step.type == PreprocessorType.REORDER_PAGES:
                _reorder(current, step.page_order)
            else:
                raise ValueError(f"Preprocessor not implemented: {step.type.value}")
    except Exception:
        if ours:
            current.close()
        raise

    return current


def _rotate(doc: fitz.Document, angle: RotateAngle) -> None:
    for page in doc:
        page.set_rotation((page.rotation + angle.value) % 360)


def _scale(doc: fitz.Document, factor: float) -> fitz.Document:
    """
    Photographic scaling: the page *and* its artwork change size together.

    Returns a new document. PDF has no in-place way to transform the content of an
    existing page, so each page is re-placed into a resized page with show_pdf_page —
    which keeps everything vector, exactly like imposition itself. Trim/bleed/art
    boxes travel with the artwork.
    """
    if factor <= 0:
        raise ValueError(f"Scale factor must be greater than 0, got {factor}")
    if factor == 1.0:
        return doc

    out = fitz.open()
    for page in doc:
        area = page.rect
        new_page = out.new_page(width=area.width * factor, height=area.height * factor)
        new_page.show_pdf_page(new_page.rect, doc, page.number)

        for name in ("trimbox", "bleedbox", "artbox"):
            box = getattr(page, name)
            if box is None or box == area:
                continue
            scaled = fitz.Rect(
                (box.x0 - area.x0) * factor, (box.y0 - area.y0) * factor,
                (box.x1 - area.x0) * factor, (box.y1 - area.y0) * factor,
            ) & new_page.rect
            if not scaled.is_empty:
                getattr(new_page, f"set_{name}")(scaled)

    return out


def _reorder(doc: fitz.Document, order_expr: str) -> None:
    """
    Reorder pages in place. Accepts "reverse" or 1-based page numbers: "4,3,2,1".

    The order must be a permutation of the whole document. Listing a subset used to
    mean "delete the rest", which is not something anyone types a *reorder* to get —
    use the Layout page range to select pages.
    """
    expr = order_expr.strip()
    if not expr:
        return

    n = len(doc)
    if expr.lower() == "reverse":
        doc.select(list(range(n - 1, -1, -1)))
        return

    try:
        new_order = [int(part.strip()) - 1 for part in expr.split(",")]
    except ValueError:
        raise ValueError(
            f"Page order must be 'reverse' or comma-separated page numbers "
            f"(e.g. '4,3,2,1'), got {order_expr!r}"
        ) from None

    outside = sorted({i + 1 for i in new_order if i < 0 or i >= n})
    if outside:
        raise ValueError(
            f"Page order refers to page(s) {', '.join(map(str, outside))}, "
            f"outside this document (1-{n})"
        )
    if sorted(new_order) != list(range(n)):
        raise ValueError(
            f"Page order must list every one of the {n} pages exactly once "
            f"(got {len(new_order)}). To impose only some pages, use the page range."
        )

    doc.select(new_order)
