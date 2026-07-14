"""
Determinism and culture-invariance.

Same input must produce the same imposition — that's what lets a re-run be trusted
to reproduce a plate. The one legitimate exception is the PDF trailer ``/ID``,
which MuPDF randomises per file because the spec defines it as a *file* identifier
rather than a content hash; so the invariant is asserted on content, not bytes.
"""

import locale
import os

import fitz
import pytest

from pressready.engine.data_model import (
    Project, LayoutSettings, LayoutType, SheetSettings, Orientation,
)
from pressready.engine.impose import impose


def _project(src):
    p = Project(source_pdf_path=src)
    p.sheet = SheetSettings(preset="A3", orientation=Orientation.LANDSCAPE)
    p.layout = LayoutSettings(layout_type=LayoutType.NUP, nup=2)
    return p


def _content(path):
    doc = fitz.open(path)
    streams = [doc[i].read_contents() for i in range(len(doc))]
    boxes = [tuple(doc[i].rect) for i in range(len(doc))]
    doc.close()
    return streams, boxes


class TestDeterminism:
    def test_same_input_gives_identical_content(self, source_pdf, out_path):
        src = source_pdf(n_pages=4)
        a, b = out_path("a.pdf"), out_path("b.pdf")
        impose(_project(src), a)
        impose(_project(src), b)
        assert _content(a) == _content(b)

    def test_only_the_file_id_differs_between_runs(self, source_pdf, out_path):
        # Pins the known/allowed source of byte variance. If a future change makes
        # output differ for any *other* reason, this test says so.
        src = source_pdf(n_pages=4)
        a, b = out_path("a.pdf"), out_path("b.pdf")
        impose(_project(src), a)
        impose(_project(src), b)

        ra, rb = open(a, "rb").read(), open(b, "rb").read()
        assert len(ra) == len(rb)
        differing = [i for i in range(len(ra)) if ra[i] != rb[i]]
        assert differing, "expected the /ID to differ"
        lo, hi = min(differing), max(differing)
        window = ra[max(0, lo - 40):hi + 40]
        assert b"/ID" in window, "bytes differ somewhere other than the trailer /ID"

    def test_booklet_is_deterministic(self, source_pdf, out_path):
        src = source_pdf(n_pages=8)
        a, b = out_path("a.pdf"), out_path("b.pdf")
        for out in (a, b):
            p = _project(src)
            p.layout.layout_type = LayoutType.BOOKLET
            impose(p, out)
        assert _content(a) == _content(b)


class TestCultureInvariance:
    """
    A comma decimal separator silently corrupts PDF number syntax. Python's own
    float formatting ignores the locale, but a C extension's need not, so this is
    checked rather than assumed. Skips where no German locale is installed.
    """

    CANDIDATES = ("de_DE.UTF-8", "de_DE.utf8", "de_DE", "German_Germany.1252", "de-DE")

    def test_output_is_identical_under_a_comma_decimal_locale(self, source_pdf, out_path):
        src = source_pdf(n_pages=4)
        plain = out_path("plain.pdf")
        impose(_project(src), plain)
        expected = _content(plain)

        previous = locale.setlocale(locale.LC_ALL)
        chosen = None
        try:
            for name in self.CANDIDATES:
                try:
                    locale.setlocale(locale.LC_ALL, name)
                    chosen = name
                    break
                except locale.Error:
                    continue
            if chosen is None:
                pytest.skip(f"no German locale installed (tried {', '.join(self.CANDIDATES)})")

            assert locale.localeconv()["decimal_point"] == ",", (
                f"{chosen} did not actually switch the decimal separator"
            )
            german = out_path("german.pdf")
            impose(_project(src), german)
            assert _content(german) == expected, (
                f"imposition output changed under {chosen} — a comma decimal leaked into the PDF"
            )
        finally:
            locale.setlocale(locale.LC_ALL, previous)

    def test_pdf_numbers_never_use_comma_decimals(self, source_pdf, out_path):
        # Locale-independent backstop for the case above: whatever the environment,
        # no number written into a content stream may carry a comma decimal.
        import re
        src = source_pdf(n_pages=4)
        out = out_path()
        impose(_project(src), out)
        doc = fitz.open(out)
        for i in range(len(doc)):
            stream = doc[i].read_contents()
            assert not re.search(rb"\d,\d", stream), f"comma decimal in sheet {i+1} content"
        doc.close()
