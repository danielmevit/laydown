"""Unit conversion and page-range parsing invariants."""

import pytest

from pressready.engine.utils import mm_to_pt, pt_to_mm, inch_to_pt, parse_page_range


class TestUnits:
    def test_mm_pt_roundtrip(self):
        for mm in (0.0, 1.0, 210.0, 297.0, 1000.0):
            assert pt_to_mm(mm_to_pt(mm)) == pytest.approx(mm)

    def test_known_conversions(self):
        assert mm_to_pt(25.4) == pytest.approx(72.0)
        assert inch_to_pt(1.0) == pytest.approx(72.0)
        assert mm_to_pt(210.0) == pytest.approx(595.28, abs=0.01)  # A4 width


class TestParsePageRange:
    def test_single(self):
        assert parse_page_range("1", 10) == [0]

    def test_range(self):
        assert parse_page_range("1-4", 10) == [0, 1, 2, 3]

    def test_mixed(self):
        assert parse_page_range("1-4,7,9-10", 10) == [0, 1, 2, 3, 6, 8, 9]

    def test_whitespace_ignored(self):
        assert parse_page_range(" 1 - 4 , 7 ", 10) == [0, 1, 2, 3, 6]

    def test_order_is_preserved_not_sorted(self):
        # A page range is also a reordering instruction; do not silently sort.
        assert parse_page_range("5,1", 10) == [4, 0]

    def test_duplicates_are_kept(self):
        # Imposing the same page twice is legitimate (e.g. repeated covers).
        assert parse_page_range("1,1", 10) == [0, 0]

    @pytest.mark.parametrize("expr", ["", "   ", "abc", "1-", "-4", "1-2-3", "0", "1,0", "x-y"])
    def test_invalid_raises(self, expr):
        with pytest.raises(ValueError):
            parse_page_range(expr, 10)

    def test_beyond_document_raises(self):
        with pytest.raises(ValueError):
            parse_page_range("11", 10)
        with pytest.raises(ValueError):
            parse_page_range("1-11", 10)

    def test_reversed_range_raises(self):
        with pytest.raises(ValueError):
            parse_page_range("4-1", 10)

    def test_bad_total_raises(self):
        with pytest.raises(ValueError):
            parse_page_range("1", 0)
