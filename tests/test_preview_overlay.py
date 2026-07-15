"""
The preview overlay must describe the sheet it is drawn on.

0.2.0 computed overlay cells from the project while rendering an imposed PDF —
two derivations of the same geometry that could disagree, which for a WYSIWYG
prepress preview means showing the user a cut line that isn't the cut line.
The overlay now comes from the imposition result itself; these tests hold that.
"""

import os

import fitz
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pressready.engine.data_model import (
    Project, LayoutSettings, LayoutType, SheetSettings, Orientation,
    SourceSettings, SourceBox,
)
from pressready.engine.impose import impose_to_temp
from pressready.ui.preview_panel import cells_from_result

from tests.helpers import page_token, word_centers


def a_project(src, **kw):
    p = Project(source_pdf_path=src)
    p.source = SourceSettings(box=kw.get("box", SourceBox.TRIM))
    p.sheet = SheetSettings(preset="A3", orientation=Orientation.LANDSCAPE)
    p.layout = LayoutSettings(
        layout_type=kw.get("layout", LayoutType.NUP), nup=kw.get("nup", 2))
    return p


def _impose(project):
    path, result = impose_to_temp(project)
    return path, result


class TestOverlayMatchesOutput:
    def test_every_overlay_cell_contains_its_page(self, source_pdf):
        src = source_pdf(n_pages=4)
        path, result = _impose(a_project(src))
        try:
            doc = fitz.open(path)
            for sheet_idx in range(result.sheets):
                found = word_centers(doc[sheet_idx])
                for cell in cells_from_result(result, sheet_idx):
                    centre = found[page_token(cell.page_num)]
                    assert cell.x0 <= centre.x <= cell.x1, (
                        f"page {cell.page_num} sits outside its overlay horizontally"
                    )
                    assert cell.y0 <= centre.y <= cell.y1, (
                        f"page {cell.page_num} sits outside its overlay vertically"
                    )
            doc.close()
        finally:
            os.unlink(path)

    def test_overlay_reports_one_cell_per_placed_page(self, source_pdf):
        src = source_pdf(n_pages=3)
        path, result = _impose(a_project(src))
        try:
            assert result.sheets == 2
            assert len(cells_from_result(result, 0)) == 2
            assert len(cells_from_result(result, 1)) == 1, (
                "the empty half of the last sheet must not be outlined"
            )
        finally:
            os.unlink(path)

    def test_overlay_tracks_the_trim_box_not_the_media_box(self, source_pdf):
        # The overlay outlines where the paper gets cut. With a trim box in play
        # that is not the same rect as the full page.
        src = source_pdf(n_pages=2, trim_inset_mm=10)
        trim_path, trim_result = _impose(a_project(src, box=SourceBox.TRIM))
        media_path, media_result = _impose(a_project(src, box=SourceBox.MEDIA))
        try:
            t = cells_from_result(trim_result, 0)[0]
            m = cells_from_result(media_result, 0)[0]
            assert (t.x0, t.y0, t.x1, t.y1) != (m.x0, m.y0, m.x1, m.y1)
        finally:
            os.unlink(trim_path)
            os.unlink(media_path)

    def test_booklet_overlay_follows_the_stitch_order(self, source_pdf):
        src = source_pdf(n_pages=8)
        path, result = _impose(a_project(src, layout=LayoutType.BOOKLET))
        try:
            assert result.sheets == 4
            first = cells_from_result(result, 0)
            # Outer side carries the last page on the left, the first on the right.
            assert [c.page_num for c in first] == [8, 1]
            assert first[0].x0 < first[1].x0
        finally:
            os.unlink(path)

    def test_overlay_is_empty_past_the_last_sheet(self, source_pdf):
        src = source_pdf(n_pages=2)
        path, result = _impose(a_project(src))
        try:
            assert cells_from_result(result, 99) == []
        finally:
            os.unlink(path)
