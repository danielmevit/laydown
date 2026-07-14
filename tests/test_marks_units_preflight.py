"""
Phase 6 — units, the new mark types, and preflight.

The mark set and the preflight idea both come from the Imposition Wizard study
(docs/ai/REFERENCE_STUDY.md): its Placeholders/ folder revealed that a custom mark is
just a PDF stamped by rule, and it has shipped a preflight dashboard for years while
PressReady only reported problems by raising at export time.
"""

import fitz
import pytest

from pressready.engine.data_model import (
    LayoutSettings, LayoutType, MarkItem, MarkType, Orientation, Project,
    SheetSettings, SourceBox, SourceSettings,
)
from pressready.engine.impose import impose
from pressready.engine.preflight import Severity, preflight
from pressready.engine.utils import Unit, mm_to_pt, pt_to_mm

from tests.helpers import make_source_pdf, word_centers


def a_project(src="", **kw):
    p = Project(source_pdf_path=src)
    p.source = SourceSettings(box=kw.pop("box", SourceBox.TRIM),
                              bleed_mm=kw.pop("bleed", 0.0))
    p.sheet = SheetSettings(
        preset=kw.pop("preset", "A3"),
        orientation=kw.pop("orientation", Orientation.LANDSCAPE),
        margin_top_mm=kw.pop("margin", 5.0),
    )
    for side in ("bottom", "left", "right"):
        setattr(p.sheet, f"margin_{side}_mm", p.sheet.margin_top_mm)
    p.layout = LayoutSettings(**kw)
    return p


# ── units ────────────────────────────────────────────

class TestUnits:
    @pytest.mark.parametrize("unit,mm,expected", [
        (Unit.MM, 210.0, 210.0),
        (Unit.CM, 210.0, 21.0),
        (Unit.INCH, 25.4, 1.0),
        (Unit.POINT, 25.4, 72.0),
    ])
    def test_converts_from_millimetres(self, unit, mm, expected):
        assert unit.from_mm(mm) == pytest.approx(expected)

    @pytest.mark.parametrize("unit", list(Unit))
    def test_round_trips(self, unit):
        for mm in (0.0, 1.0, 5.5, 210.0, 1000.0):
            assert unit.to_mm(unit.from_mm(mm)) == pytest.approx(mm)

    def test_letter_width_in_inches(self):
        assert Unit.INCH.from_mm(215.9) == pytest.approx(8.5)

    def test_each_unit_offers_a_sensible_step_and_precision(self):
        for unit in Unit:
            assert unit.decimals >= 0
            assert unit.step > 0
            assert unit.suffix.strip() == unit.value

    def test_the_model_still_stores_millimetres(self):
        # Units are a display concern only; nothing downstream should have to ask.
        sheet = SheetSettings(preset="Letter")
        assert sheet.sheet_size_mm() == (279.4, 215.9)


# ── new marks ────────────────────────────────────────

def _black_points(page):
    pts = []
    for drawing in page.get_drawings():
        if drawing.get("color") != (0.0, 0.0, 0.0):
            continue
        for item in drawing["items"]:
            for element in item[1:]:
                if isinstance(element, fitz.Point):
                    pts.append(element)
    return pts


class TestNewMarks:
    def test_gap_crop_marks_reach_the_sheet_edge(self, source_pdf, out_path):
        src = source_pdf(n_pages=4)
        project = a_project(src, nup=4)
        project.marks = [MarkItem(mark_type=MarkType.GAP_CROP_MARKS)]
        out = out_path()
        impose(project, out)

        pts = _black_points(fitz.open(out)[0])
        assert pts, "no gap crop marks drawn"
        # They run out to the sheet edge, unlike ordinary corner crop marks.
        assert min(p.x for p in pts) == pytest.approx(0.0, abs=0.5)
        assert min(p.y for p in pts) == pytest.approx(0.0, abs=0.5)

    def test_colour_bar_paints_patches_in_the_margin(self, source_pdf, out_path):
        src = source_pdf(n_pages=2)
        project = a_project(src, margin=12.0)
        project.marks = [MarkItem(mark_type=MarkType.COLOR_BAR, patch_size_mm=5.0)]
        out = out_path()
        impose(project, out)

        page = fitz.open(out)[0]
        filled = [d for d in page.get_drawings() if d.get("fill")]
        assert len(filled) >= 8, "expected a patch per ink plus a grey ramp"
        for drawing in filled[:8]:
            assert drawing["rect"].y1 <= mm_to_pt(12.0) + 1, "bar should sit in the margin"

    def test_colour_bar_is_skipped_when_the_margin_cannot_hold_it(self, source_pdf, out_path):
        src = source_pdf(n_pages=2)
        project = a_project(src, margin=2.0)
        project.marks = [MarkItem(mark_type=MarkType.COLOR_BAR, patch_size_mm=5.0)]
        out = out_path()
        impose(project, out)  # must not raise or overprint
        page = fitz.open(out)[0]
        patches = [d for d in page.get_drawings()
                   if d.get("fill") in [(0, 1, 1), (1, 0, 1)]]
        assert not patches

    def test_perforation_marks_run_up_the_fold(self, source_pdf, out_path):
        src = source_pdf(n_pages=8)
        project = a_project(src, layout_type=LayoutType.BOOKLET)
        project.marks = [MarkItem(mark_type=MarkType.PERFORATION_MARKS)]
        out = out_path()
        impose(project, out)
        pts = _black_points(fitz.open(out)[0])
        assert pts, "no perforation rule drawn"
        assert len({round(p.x, 1) for p in pts}) == 1, "the rule should be vertical"

    def test_custom_mark_stamps_a_pdf_onto_the_sheet(self, source_pdf, out_path, tmp_path):
        art = str(tmp_path / "bullseye.pdf")
        doc = fitz.open()
        # Generous page: text wider than the art box gets clipped by the XObject and
        # comes back out truncated, which looks exactly like a mark that never drew.
        page = doc.new_page(width=200, height=60)
        page.insert_text((5, 35), "TARGETMARK", fontsize=10)
        doc.save(art)
        doc.close()

        src = source_pdf(n_pages=2)
        project = a_project(src)
        project.marks = [MarkItem(
            mark_type=MarkType.CUSTOM_MARK, mark_pdf_path=art,
            mark_width_mm=30.0, mark_x_mm=8.0, mark_y_mm=8.0)]
        out = out_path()
        impose(project, out)

        found = word_centers(fitz.open(out)[0])
        assert "TARGETMARK" in found, "the custom mark PDF did not reach the sheet"
        assert found["TARGETMARK"].x < mm_to_pt(40)

    def test_custom_mark_keeps_the_artwork_proportions(self, source_pdf, out_path, tmp_path):
        art = str(tmp_path / "wide.pdf")
        doc = fitz.open()
        doc.new_page(width=100, height=25).draw_rect(
            fitz.Rect(0, 0, 100, 25), fill=(0, 0, 1), color=None)
        doc.save(art)
        doc.close()

        src = source_pdf(n_pages=2)
        project = a_project(src)
        project.marks = [MarkItem(mark_type=MarkType.CUSTOM_MARK, mark_pdf_path=art,
                                  mark_width_mm=40.0, mark_x_mm=5.0, mark_y_mm=5.0)]
        out = out_path()
        impose(project, out)

        blue = [d["rect"] for d in fitz.open(out)[0].get_drawings()
                if d.get("fill") == (0.0, 0.0, 1.0)]
        assert blue
        assert blue[0].width / blue[0].height == pytest.approx(4.0, abs=0.1)

    def test_a_missing_mark_pdf_does_not_break_the_job(self, source_pdf, out_path):
        src = source_pdf(n_pages=2)
        project = a_project(src)
        project.marks = [MarkItem(mark_type=MarkType.CUSTOM_MARK,
                                  mark_pdf_path="/nowhere/at/all.pdf")]
        out = out_path()
        assert impose(project, out) == 1  # the sheet is still right without the mark

    def test_a_corrupt_mark_pdf_does_not_break_the_job(self, source_pdf, out_path, tmp_path):
        junk = tmp_path / "junk.pdf"
        junk.write_bytes(b"this is not a PDF at all")
        src = source_pdf(n_pages=2)
        project = a_project(src)
        project.marks = [MarkItem(mark_type=MarkType.CUSTOM_MARK, mark_pdf_path=str(junk))]
        assert impose(project, out_path()) == 1


# ── preflight ────────────────────────────────────────

class TestPreflight:
    def _findings(self, project, src=None):
        doc = fitz.open(src) if src else None
        try:
            return preflight(project, doc)
        finally:
            if doc:
                doc.close()

    def test_a_healthy_job_reports_nothing_serious(self, source_pdf):
        src = source_pdf(n_pages=4, w_mm=210, h_mm=297)
        # 2-up A4 onto A3 landscape is the case the tool is built for.
        findings = self._findings(a_project(src), src)
        assert not [f for f in findings if f.severity is Severity.ERROR]

    def test_impossible_margins_are_reported_before_export(self, source_pdf):
        # This used to surface only as an exception after the operator hit Generate.
        findings = self._findings(a_project(margin=250.0))
        errors = [f for f in findings if f.severity is Severity.ERROR]
        assert errors and "too large" in errors[0].message

    def test_serious_scaling_down_is_warned_about(self, source_pdf):
        src = source_pdf(n_pages=4, w_mm=210, h_mm=297)
        findings = self._findings(a_project(src, preset="A4", nup=4), src)
        scaling = [f for f in findings if "scaled to" in f.message]
        assert scaling and scaling[0].severity is Severity.WARNING

    def test_the_canonical_job_is_not_warned_about(self, source_pdf):
        # A4 two-up on A3 with any margin at all lands near 97%. That is the job this
        # tool exists for; warning about it would teach the operator to ignore the
        # strip, so slight scaling is a note and only a real reduction is a warning.
        src = source_pdf(n_pages=4, w_mm=210, h_mm=297)
        findings = self._findings(a_project(src), src)
        assert not [f for f in findings if f.severity is Severity.WARNING]
        scaling = [f for f in findings if "scaled to" in f.message]
        assert scaling and scaling[0].severity is Severity.NOTE

    def test_a_missing_trim_box_is_a_note_not_an_error(self, source_pdf):
        src = source_pdf(n_pages=2, trim_inset_mm=0)
        findings = self._findings(a_project(src), src)
        notes = [f for f in findings if "no trim box" in f.message]
        assert notes and notes[0].severity is Severity.NOTE

    def test_a_real_trim_box_produces_no_such_note(self, source_pdf):
        src = source_pdf(n_pages=2, trim_inset_mm=10)
        findings = self._findings(a_project(src), src)
        assert not [f for f in findings if "no trim box" in f.message]

    def test_bleed_beyond_the_artwork_is_warned_about(self, source_pdf):
        src = source_pdf(n_pages=2, trim_inset_mm=3)
        findings = self._findings(a_project(src, bleed=20.0), src)
        warnings = [f for f in findings if "bleed" in f.message.lower()]
        assert warnings and warnings[0].severity is Severity.WARNING

    def test_a_page_count_that_does_not_fold_is_noted(self, source_pdf):
        src = source_pdf(n_pages=6)
        findings = self._findings(a_project(src, layout_type=LayoutType.BOOKLET), src)
        assert any("padded to 8" in f.message for f in findings)

    def test_a_booklet_that_folds_exactly_is_not_noted(self, source_pdf):
        src = source_pdf(n_pages=8)
        findings = self._findings(a_project(src, layout_type=LayoutType.BOOKLET), src)
        assert not [f for f in findings if "padded" in f.message]

    def test_mixed_page_sizes_are_warned_about(self, tmp_path):
        path = str(tmp_path / "mixed.pdf")
        doc = fitz.open()
        doc.new_page(width=mm_to_pt(210), height=mm_to_pt(297))
        doc.new_page(width=mm_to_pt(297), height=mm_to_pt(420))
        doc.save(path)
        doc.close()
        findings = self._findings(a_project(path), path)
        assert any("different page sizes" in f.message for f in findings)

    def test_findings_are_ordered_worst_first(self, source_pdf):
        src = source_pdf(n_pages=6, trim_inset_mm=0)
        project = a_project(src, layout_type=LayoutType.BOOKLET, preset="A5")
        findings = self._findings(project, src)
        ranks = [list(Severity).index(f.severity) for f in findings]
        assert ranks == sorted(ranks)

    def test_preflight_works_with_no_pdf_loaded(self):
        assert preflight(a_project()) == []

    def test_every_finding_explains_itself(self, source_pdf):
        src = source_pdf(n_pages=6, trim_inset_mm=0)
        for finding in self._findings(a_project(src, layout_type=LayoutType.BOOKLET), src):
            assert finding.message and not finding.message.endswith(".")
            assert str(finding).startswith(finding.severity.value)
