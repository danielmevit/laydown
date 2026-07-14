"""
The ground-truth round-trip: impose a known source, read the output back, and
check every source page landed where the geometry says it should.

This is the harness every later layout change is measured against (ROADMAP.md
Phase 1). Cell geometry is re-derived here rather than imported, so the test can
disagree with the engine — which is the entire point of having it.
"""

import fitz
import pytest

from pressready.engine.data_model import (
    Project, LayoutSettings, LayoutType, SheetSettings, Orientation,
)
from pressready.engine.impose import impose, booklet_page_order
from pressready.engine.utils import mm_to_pt

from tests.helpers import (
    page_token, corner_token, word_centers, project_point, assert_near,
)


# ── geometry, re-derived independently of the engine ──

def nup_cells(sheet_w, sheet_h, margins_pt, gh, gv, cols, rows, count):
    ml, mr, mt, mb = margins_pt
    cw = (sheet_w - ml - mr - (cols - 1) * gh) / cols
    ch = (sheet_h - mt - mb - (rows - 1) * gv) / rows
    cells = []
    for ci in range(count):
        col, row = ci % cols, ci // cols
        x0 = ml + col * (cw + gh)
        y0 = mt + row * (ch + gv)
        cells.append(fitz.Rect(x0, y0, x0 + cw, y0 + ch))
    return cells


def a_project(src, *, nup=2, layout=LayoutType.NUP, preset="A3",
              orientation=Orientation.LANDSCAPE, margin=5.0, gh=0.0, gv=0.0, page_range=""):
    p = Project(source_pdf_path=src)
    p.sheet = SheetSettings(
        preset=preset, orientation=orientation,
        margin_top_mm=margin, margin_bottom_mm=margin,
        margin_left_mm=margin, margin_right_mm=margin,
    )
    p.layout = LayoutSettings(
        layout_type=layout, nup=nup, gutter_h_mm=gh, gutter_v_mm=gv, page_range=page_range,
    )
    return p


# ── N-Up ─────────────────────────────────────────────

class TestNUpPlacement:
    def test_2up_four_pages_makes_two_sheets(self, source_pdf, out_path):
        src = source_pdf(n_pages=4)
        out = out_path()
        assert impose(a_project(src), out) == 2

        doc = fitz.open(out)
        assert len(doc) == 2
        # A3 landscape
        assert doc[0].rect.width == pytest.approx(mm_to_pt(420), abs=0.5)
        assert doc[0].rect.height == pytest.approx(mm_to_pt(297), abs=0.5)
        doc.close()

    def test_2up_pages_land_in_reading_order_at_exact_positions(self, source_pdf, out_path):
        src = source_pdf(n_pages=4, w_mm=210, h_mm=297)
        out = out_path()
        impose(a_project(src), out)

        src_doc = fitz.open(src)
        src_box = src_doc[0].rect
        out_doc = fitz.open(out)

        m = mm_to_pt(5.0)
        cells = nup_cells(mm_to_pt(420), mm_to_pt(297), (m, m, m, m), 0, 0, 2, 1, 2)

        for sheet_idx in range(2):
            found = word_centers(out_doc[sheet_idx])
            for cell_idx, cell in enumerate(cells):
                pageno = sheet_idx * 2 + cell_idx + 1
                src_found = word_centers(src_doc[pageno - 1])

                token = page_token(pageno)
                assert token in found, f"sheet {sheet_idx+1} is missing page {pageno}"
                assert_near(
                    found[token], project_point(src_found[token], src_box, cell),
                    what=f"page {pageno} centre on sheet {sheet_idx+1}",
                )

                for corner in ("TL", "TR", "BL", "BR"):
                    ct = corner_token(pageno, corner)
                    assert_near(
                        found[ct], project_point(src_found[ct], src_box, cell),
                        what=f"page {pageno} {corner} on sheet {sheet_idx+1}",
                    )
        src_doc.close()
        out_doc.close()

    def test_4up_fills_two_rows(self, source_pdf, out_path):
        src = source_pdf(n_pages=4)
        out = out_path()
        assert impose(a_project(src, nup=4), out) == 1

        src_doc = fitz.open(src)
        src_box = src_doc[0].rect
        out_doc = fitz.open(out)
        m = mm_to_pt(5.0)
        cells = nup_cells(mm_to_pt(420), mm_to_pt(297), (m, m, m, m), 0, 0, 2, 2, 4)

        found = word_centers(out_doc[0])
        for cell_idx, cell in enumerate(cells):
            pageno = cell_idx + 1
            src_found = word_centers(src_doc[pageno - 1])
            assert_near(found[page_token(pageno)],
                        project_point(src_found[page_token(pageno)], src_box, cell),
                        what=f"4-up page {pageno}")
        src_doc.close()
        out_doc.close()

    def test_gutter_pushes_cells_apart(self, source_pdf, out_path):
        src = source_pdf(n_pages=2)
        out = out_path()
        impose(a_project(src, gh=20.0), out)

        src_doc = fitz.open(src)
        src_box = src_doc[0].rect
        out_doc = fitz.open(out)
        m, g = mm_to_pt(5.0), mm_to_pt(20.0)
        cells = nup_cells(mm_to_pt(420), mm_to_pt(297), (m, m, m, m), g, 0, 2, 1, 2)

        found = word_centers(out_doc[0])
        for cell_idx, cell in enumerate(cells):
            pageno = cell_idx + 1
            src_found = word_centers(src_doc[pageno - 1])
            assert_near(found[page_token(pageno)],
                        project_point(src_found[page_token(pageno)], src_box, cell),
                        what=f"gutter page {pageno}")

        # And the gap between the two placed pages really is the gutter.
        right_of_left = found[corner_token(1, "TR")].x
        left_of_right = found[corner_token(2, "TL")].x
        assert left_of_right - right_of_left > g * 0.8
        src_doc.close()
        out_doc.close()

    def test_odd_page_count_leaves_last_cell_empty(self, source_pdf, out_path):
        src = source_pdf(n_pages=3)
        out = out_path()
        assert impose(a_project(src), out) == 2

        out_doc = fitz.open(out)
        last = word_centers(out_doc[1])
        assert page_token(3) in last
        assert page_token(4) not in last
        out_doc.close()

    def test_page_range_selects_and_orders(self, source_pdf, out_path):
        src = source_pdf(n_pages=8)
        out = out_path()
        assert impose(a_project(src, page_range="5,2"), out) == 1

        out_doc = fitz.open(out)
        found = word_centers(out_doc[0])
        assert page_token(5) in found and page_token(2) in found
        assert page_token(1) not in found
        # "5,2" means 5 first: it must land in the left cell.
        assert found[page_token(5)].x < found[page_token(2)].x
        out_doc.close()

    def test_content_stays_inside_the_margins(self, source_pdf, out_path):
        src = source_pdf(n_pages=4)
        out = out_path()
        impose(a_project(src, margin=15.0), out)

        out_doc = fitz.open(out)
        m = mm_to_pt(15.0)
        sheet = out_doc[0].rect
        for token, centre in word_centers(out_doc[0]).items():
            assert sheet.x0 + m <= centre.x <= sheet.x1 - m, f"{token} outside left/right margin"
            assert sheet.y0 + m <= centre.y <= sheet.y1 - m, f"{token} outside top/bottom margin"
        out_doc.close()

    def test_impossible_margins_raise(self, source_pdf, out_path):
        src = source_pdf(n_pages=2)
        with pytest.raises(ValueError, match="too large"):
            impose(a_project(src, margin=250.0), out_path())


# ── Booklet ──────────────────────────────────────────

class TestBookletPlacement:
    def test_eight_pages_make_four_sides(self, source_pdf, out_path):
        src = source_pdf(n_pages=8)
        out = out_path()
        assert impose(a_project(src, layout=LayoutType.BOOKLET), out) == 4

    def test_pages_follow_the_saddle_stitch_order(self, source_pdf, out_path):
        src = source_pdf(n_pages=8)
        out = out_path()
        impose(a_project(src, layout=LayoutType.BOOKLET), out)

        out_doc = fitz.open(out)
        for side_idx, (left, right) in enumerate(booklet_page_order(8)):
            found = word_centers(out_doc[side_idx])
            lt, rt = page_token(left + 1), page_token(right + 1)
            assert lt in found and rt in found, f"side {side_idx+1} missing its pages"
            assert found[lt].x < found[rt].x, (
                f"side {side_idx+1}: page {left+1} must sit left of page {right+1}"
            )
        out_doc.close()

    def test_short_booklet_leaves_blanks_and_keeps_every_page(self, source_pdf, out_path):
        src = source_pdf(n_pages=6)
        out = out_path()
        assert impose(a_project(src, layout=LayoutType.BOOKLET), out) == 4

        out_doc = fitz.open(out)
        seen = set()
        for page in out_doc:
            seen |= {w for w in word_centers(page) if w.startswith("PG")}
        assert seen == {page_token(i) for i in range(1, 7)}
        out_doc.close()
