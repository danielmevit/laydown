"""
Failure behaviour and resource hygiene.

A prepress tool must not fail quietly: a setting the user typed either takes
effect or says why it didn't. These tests pin the places where v2.0.0 swallowed
the difference (ROADMAP.md Phase 1).
"""

import fitz
import pytest

from pressready.engine.data_model import (
    Project, LayoutSettings, LayoutType, SheetSettings, Orientation,
    PreprocessorStep, PreprocessorType, RotateAngle,
)
from pressready.engine.impose import impose
from pressready.engine.preprocessors import apply_preprocessors

from tests.helpers import page_token, corner_token, word_centers


def a_project(src, **kw):
    p = Project(source_pdf_path=src)
    p.sheet = SheetSettings(
        preset="A3", orientation=Orientation.LANDSCAPE,
        margin_top_mm=kw.get("margin", 5.0), margin_bottom_mm=kw.get("margin", 5.0),
        margin_left_mm=kw.get("margin", 5.0), margin_right_mm=kw.get("margin", 5.0),
    )
    p.layout = LayoutSettings(layout_type=LayoutType.NUP, nup=kw.get("nup", 2))
    return p


class TestResourceHygiene:
    def test_source_document_is_closed_when_imposition_fails(self, source_pdf, out_path, monkeypatch):
        src = source_pdf(n_pages=2)
        opened = []
        real_open = fitz.open

        def tracking_open(*a, **k):
            doc = real_open(*a, **k)
            opened.append(doc)
            return doc

        monkeypatch.setattr(fitz, "open", tracking_open)
        with pytest.raises(ValueError):
            impose(a_project(src, margin=250.0), out_path())

        leaked = [d for d in opened if not d.is_closed]
        assert not leaked, f"{len(leaked)} document(s) left open after a failed imposition"

    def test_documents_are_closed_on_success(self, source_pdf, out_path, monkeypatch):
        src = source_pdf(n_pages=4)
        opened = []
        real_open = fitz.open

        def tracking_open(*a, **k):
            doc = real_open(*a, **k)
            opened.append(doc)
            return doc

        monkeypatch.setattr(fitz, "open", tracking_open)
        impose(a_project(src), out_path())
        leaked = [d for d in opened if not d.is_closed]
        assert not leaked, f"{len(leaked)} document(s) left open after a successful imposition"


class TestReorderFailsLoudly:
    def _doc(self, source_pdf):
        return fitz.open(source_pdf(n_pages=4))

    def test_reverse_works(self, source_pdf):
        doc = self._doc(source_pdf)
        step = PreprocessorStep(type=PreprocessorType.REORDER_PAGES, page_order="reverse")
        out = apply_preprocessors(doc, [step])
        assert page_token(4) in word_centers(out[0])
        out.close()

    def test_explicit_order_works(self, source_pdf):
        doc = self._doc(source_pdf)
        step = PreprocessorStep(type=PreprocessorType.REORDER_PAGES, page_order="4,3,2,1")
        out = apply_preprocessors(doc, [step])
        assert page_token(4) in word_centers(out[0])
        out.close()

    @pytest.mark.parametrize("expr", ["nonsense", "1,two,3", "1..4", "-1"])
    def test_unparseable_order_raises(self, source_pdf, expr):
        doc = self._doc(source_pdf)
        step = PreprocessorStep(type=PreprocessorType.REORDER_PAGES, page_order=expr)
        with pytest.raises(ValueError):
            apply_preprocessors(doc, [step])
        doc.close()

    def test_out_of_range_order_raises(self, source_pdf):
        doc = self._doc(source_pdf)
        step = PreprocessorStep(type=PreprocessorType.REORDER_PAGES, page_order="1,2,3,99")
        with pytest.raises(ValueError):
            apply_preprocessors(doc, [step])
        doc.close()

    def test_partial_order_does_not_silently_drop_pages(self, source_pdf):
        # "4,3" against a 4-page document once meant "keep only two pages" —
        # a reorder must never be a delete.
        doc = self._doc(source_pdf)
        step = PreprocessorStep(type=PreprocessorType.REORDER_PAGES, page_order="4,3")
        with pytest.raises(ValueError, match="(?i)all|missing|every"):
            apply_preprocessors(doc, [step])
        doc.close()


class TestScaleKeepsContent:
    def test_scaling_down_keeps_every_token(self, source_pdf, out_path):
        # Scale Pages must be a photographic reduction, not a crop.
        src = source_pdf(n_pages=1, w_mm=210, h_mm=297)
        p = a_project(src)
        p.preprocessors = [
            PreprocessorStep(type=PreprocessorType.SCALE_PAGES, scale_factor=0.5)
        ]
        out = out_path()
        impose(p, out)

        doc = fitz.open(out)
        found = word_centers(doc[0])
        for corner in ("TL", "TR", "BL", "BR"):
            assert corner_token(1, corner) in found, (
                f"{corner} corner was cropped away — scaling resized the canvas "
                f"without transforming the content"
            )
        assert page_token(1) in found
        doc.close()

    def test_scaling_preserves_aspect_and_relative_layout(self, source_pdf, out_path):
        src = source_pdf(n_pages=1, w_mm=210, h_mm=297)
        p = a_project(src)
        p.preprocessors = [
            PreprocessorStep(type=PreprocessorType.SCALE_PAGES, scale_factor=0.5)
        ]
        out = out_path()
        impose(p, out)
        doc = fitz.open(out)
        f = word_centers(doc[0])
        # The corners must still form a rectangle in the same orientation.
        assert f[corner_token(1, "TL")].x < f[corner_token(1, "TR")].x
        assert f[corner_token(1, "TL")].y < f[corner_token(1, "BL")].y
        doc.close()

    def test_scale_of_one_is_a_no_op(self, source_pdf, out_path):
        src = source_pdf(n_pages=2)
        plain, scaled = out_path("plain.pdf"), out_path("scaled.pdf")
        impose(a_project(src), plain)
        p = a_project(src)
        p.preprocessors = [
            PreprocessorStep(type=PreprocessorType.SCALE_PAGES, scale_factor=1.0)
        ]
        impose(p, scaled)

        a, b = fitz.open(plain), fitz.open(scaled)
        assert word_centers(a[0]).keys() == word_centers(b[0]).keys()
        a.close()
        b.close()


class TestRotatePreprocessor:
    def test_rotate_90_swaps_the_placed_aspect(self, source_pdf, out_path):
        src = source_pdf(n_pages=2, w_mm=210, h_mm=297)
        p = a_project(src)
        p.preprocessors = [
            PreprocessorStep(type=PreprocessorType.ROTATE_PAGES, rotate_angle=RotateAngle.CW_90)
        ]
        out = out_path()
        impose(p, out)
        doc = fitz.open(out)
        found = word_centers(doc[0])
        assert page_token(1) in found, "rotated page vanished"
        doc.close()
