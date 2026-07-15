"""
Box-aware imposition (ROADMAP.md Phase 2).

A press-ready PDF describes its finished page with a TrimBox and paints artwork out
past it to a BleedBox. 0.2.0 imposed the MediaBox unconditionally, so for exactly
the files this tool exists to handle it placed the wrong area and marked the wrong
edge. These tests pin the box semantics.
"""

import fitz
import pytest

from pressready.engine.data_model import (
    Project, LayoutSettings, LayoutType, SheetSettings, Orientation,
    SourceSettings, SourceBox, MarkItem, MarkType,
)
from pressready.engine.geometry import cell_grid, fitted_rect, source_boxes, target_rect
from pressready.engine.impose import impose
from pressready.engine.utils import mm_to_pt

from tests.helpers import (
    page_token, corner_token, SLUG_TOKEN, word_centers, project_point, assert_near,
)


def a_project(src, *, box=SourceBox.TRIM, bleed=0.0, preset="A3",
              orientation=Orientation.LANDSCAPE, nup=2, margin=5.0, marks=None):
    p = Project(source_pdf_path=src)
    p.source = SourceSettings(box=box, bleed_mm=bleed)
    p.sheet = SheetSettings(
        preset=preset, orientation=orientation,
        margin_top_mm=margin, margin_bottom_mm=margin,
        margin_left_mm=margin, margin_right_mm=margin,
    )
    p.layout = LayoutSettings(layout_type=LayoutType.NUP, nup=nup)
    p.marks = marks or []
    return p


def black_mark_points(page):
    """Every point of the black vector marks on *page* (source art is not black)."""
    pts = []
    for drawing in page.get_drawings():
        if drawing.get("color") != (0.0, 0.0, 0.0):
            continue
        for item in drawing["items"]:
            for element in item[1:]:
                if isinstance(element, fitz.Point):
                    pts.append(element)
                elif isinstance(element, fitz.Rect):
                    pts += [fitz.Point(element.x0, element.y0),
                            fitz.Point(element.x1, element.y1)]
    return pts


def bbox_of(points):
    return fitz.Rect(min(p.x for p in points), min(p.y for p in points),
                     max(p.x for p in points), max(p.y for p in points))


class TestBoxSelection:
    def test_trim_box_is_what_lands_on_the_cell(self, source_pdf, out_path):
        src = source_pdf(n_pages=2, trim_inset_mm=10)
        out = out_path()
        impose(a_project(src, box=SourceBox.TRIM), out)

        src_doc = fitz.open(src)
        trim = src_doc[0].trimbox
        assert trim != src_doc[0].mediabox, "fixture should have a real trim box"

        out_doc = fitz.open(out)
        cell = cell_grid(a_project(src), 2, 1)[0]
        found, src_found = word_centers(out_doc[0]), word_centers(src_doc[0])

        for corner in ("TL", "TR", "BL", "BR"):
            token = corner_token(1, corner)
            assert_near(found[token], project_point(src_found[token], trim, cell),
                        what=f"{corner} under TrimBox imposition")
        src_doc.close()
        out_doc.close()

    def test_media_box_places_the_whole_sheet_instead(self, source_pdf, out_path):
        src = source_pdf(n_pages=2, trim_inset_mm=10)
        out = out_path()
        impose(a_project(src, box=SourceBox.MEDIA), out)

        src_doc = fitz.open(src)
        media = src_doc[0].mediabox
        out_doc = fitz.open(out)
        cell = cell_grid(a_project(src), 2, 1)[0]
        found, src_found = word_centers(out_doc[0]), word_centers(src_doc[0])

        for corner in ("TL", "TR", "BL", "BR"):
            token = corner_token(1, corner)
            assert_near(found[token], project_point(src_found[token], media, cell),
                        what=f"{corner} under MediaBox imposition")
        src_doc.close()
        out_doc.close()

    def test_the_two_boxes_actually_place_pages_differently(self, source_pdf, out_path):
        # Guards against both settings silently collapsing to the same behaviour.
        # Probed at a corner, not the centre: the trim box is inset symmetrically, so
        # the page centre maps to the cell centre either way and proves nothing.
        src = source_pdf(n_pages=2, trim_inset_mm=10)
        trim_out, media_out = out_path("trim.pdf"), out_path("media.pdf")
        impose(a_project(src, box=SourceBox.TRIM), trim_out)
        impose(a_project(src, box=SourceBox.MEDIA), media_out)

        token = corner_token(1, "TL")
        t = word_centers(fitz.open(trim_out)[0])[token]
        m = word_centers(fitz.open(media_out)[0])[token]
        assert abs(t.x - m.x) > 1.0 or abs(t.y - m.y) > 1.0, (
            "TrimBox and MediaBox imposition produced the same placement"
        )

    def test_trim_box_clips_away_content_outside_it(self, source_pdf, out_path):
        src = source_pdf(n_pages=2, trim_inset_mm=10, slug=True)
        out = out_path()
        impose(a_project(src, box=SourceBox.TRIM), out)
        assert SLUG_TOKEN not in word_centers(fitz.open(out)[0]), (
            "a slug mark outside the trim box must not reach the press sheet"
        )

    def test_media_box_keeps_that_same_content(self, source_pdf, out_path):
        src = source_pdf(n_pages=2, trim_inset_mm=10, slug=True)
        out = out_path()
        impose(a_project(src, box=SourceBox.MEDIA), out)
        assert SLUG_TOKEN in word_centers(fitz.open(out)[0])

    def test_plain_pdf_without_boxes_is_unharmed_by_the_trim_default(self, source_pdf, out_path):
        # TrimBox falls back to CropBox then MediaBox, so defaulting to it is safe
        # for the ordinary PDFs that carry no box information at all.
        src = source_pdf(n_pages=4, trim_inset_mm=0)
        trim_out, media_out = out_path("trim.pdf"), out_path("media.pdf")
        impose(a_project(src, box=SourceBox.TRIM), trim_out)
        impose(a_project(src, box=SourceBox.MEDIA), media_out)

        a, b = fitz.open(trim_out), fitz.open(media_out)
        for i in range(len(a)):
            assert word_centers(a[i]).keys() == word_centers(b[i]).keys()
            for token, centre in word_centers(a[i]).items():
                assert_near(centre, word_centers(b[i])[token], tol=0.01, what=token)
        a.close()
        b.close()


class TestBleed:
    def test_bleed_puts_ink_outside_the_trim_edge(self, source_pdf, out_path):
        # Rendered, not inspected: bleed changes only the *clip*, and both settings
        # share one affine transform, so get_drawings() reports identical unclipped
        # path extents for each. Only the raster shows what actually reaches paper.
        src = source_pdf(n_pages=2, trim_inset_mm=10, bleed_mm=5)
        plain, bled = out_path("plain.pdf"), out_path("bled.pdf")
        impose(a_project(src, bleed=0.0), plain)
        impose(a_project(src, bleed=5.0), bled)

        project = a_project(src)
        cell = cell_grid(project, 2, 1)[0]
        src_page = fitz.open(src)[0]
        place, _ = source_boxes(src_page, SourceSettings())
        _, trim = target_rect(cell, place, place)

        probe_x = int(trim.x0 - 5)                  # just outside the cut line
        probe_y = int((trim.y0 + trim.y1) / 2)
        assert probe_x > 0

        def pixel_at(path):
            page = fitz.open(path)[0]
            return page.get_pixmap(alpha=False).pixel(probe_x, probe_y)  # 72dpi = 1px/pt

        assert pixel_at(plain) == (255, 255, 255), (
            "without bleed, beyond the trim line must be bare paper"
        )
        assert pixel_at(bled) != (255, 255, 255), (
            "with bleed, ink must carry past the trim line so an off cut still hits it"
        )

    def test_bleed_keeps_the_trim_where_it_was(self, source_pdf, out_path):
        # Bleed adds ink around the page; it must not move the page.
        src = source_pdf(n_pages=2, trim_inset_mm=10, bleed_mm=5)
        plain, bled = out_path("plain.pdf"), out_path("bled.pdf")
        impose(a_project(src, bleed=0.0), plain)
        impose(a_project(src, bleed=5.0), bled)

        a = word_centers(fitz.open(plain)[0])
        b = word_centers(fitz.open(bled)[0])
        for token in (page_token(1), corner_token(1, "TL"), corner_token(1, "BR")):
            assert_near(b[token], a[token], tol=0.5, what=f"{token} moved when bleed was added")

    def test_bleed_is_clamped_to_the_page(self, source_pdf, out_path):
        # A bleed larger than the source can supply must not crash or distort.
        src = source_pdf(n_pages=2, trim_inset_mm=2)
        out = out_path()
        impose(a_project(src, bleed=500.0), out)
        assert page_token(1) in word_centers(fitz.open(out)[0])


class TestMarksFollowTheTrimRect:
    def test_crop_marks_track_the_page_not_the_cell(self, source_pdf, out_path):
        # A square page in a tall cell is letterboxed: the cell is far taller than
        # the page. Crop marks drawn on the cell would sit off the paper entirely.
        src = source_pdf(n_pages=2, w_mm=200, h_mm=200)
        project = a_project(
            src, preset="A4", orientation=Orientation.PORTRAIT,
            marks=[MarkItem(mark_type=MarkType.CROP_MARKS)],
        )
        out = out_path()
        impose(project, out)

        cell = cell_grid(project, 2, 1)[0]
        src_doc = fitz.open(src)
        trim = fitted_rect(cell, src_doc[0].rect.width, src_doc[0].rect.height)
        assert trim.height < cell.height / 2, "fixture should letterbox heavily"

        marks = bbox_of(black_mark_points(fitz.open(out)[0]))
        reach = mm_to_pt(5.0 + 3.0)  # default crop length + offset

        assert marks.y0 == pytest.approx(trim.y0 - reach, abs=1.0), (
            "crop marks are not on the page's top edge"
        )
        assert marks.y1 == pytest.approx(trim.y1 + reach, abs=1.0), (
            "crop marks are not on the page's bottom edge"
        )
        assert marks.y0 > cell.y0, "crop marks are following the cell, not the page"
        src_doc.close()


class TestGeometryUnits:
    def test_target_rect_returns_the_trim_not_the_cell(self):
        cell = fitz.Rect(0, 0, 100, 300)
        place = fitz.Rect(0, 0, 200, 200)
        target, trim = target_rect(cell, place, place)
        assert target == trim
        assert (trim.width, trim.height) == pytest.approx((100, 100))
        assert trim.y0 == pytest.approx(100)  # centred in the tall cell

    def test_target_rect_grows_the_target_for_bleed_only(self):
        cell = fitz.Rect(0, 0, 200, 200)
        place = fitz.Rect(10, 10, 110, 110)   # 100×100
        clip = fitz.Rect(0, 0, 120, 120)      # 10 units of bleed all round
        target, trim = target_rect(cell, place, clip)
        assert (trim.width, trim.height) == pytest.approx((200, 200))
        # scale is 2×, so 10 units of bleed becomes 20 on the sheet
        assert target.x0 == pytest.approx(trim.x0 - 20)
        assert target.x1 == pytest.approx(trim.x1 + 20)
        assert target.width / target.height == pytest.approx(clip.width / clip.height)

    def test_source_boxes_defaults_to_the_whole_page_without_boxes(self, source_pdf):
        src = source_pdf(n_pages=1, trim_inset_mm=0)
        page = fitz.open(src)[0]
        place, clip = source_boxes(page, SourceSettings())
        assert place == page.rect
        assert clip == place
