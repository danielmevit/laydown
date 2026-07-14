"""
Saddle-stitch ordering invariants.

These are the truths that must survive any future tuning of the booklet code:
every page is imposed exactly once, facing pages sum to a constant (that is what
makes a folded signature read in order), and padding only appears when the page
count isn't a multiple of four.
"""

import pytest

from pressready.engine.impose import booklet_page_order


def _padded(n: int) -> int:
    return ((n + 3) // 4) * 4


class TestBookletPageOrder:
    @pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6, 7, 8, 12, 16, 17, 40])
    def test_every_page_appears_exactly_once(self, n):
        flat = [p for pair in booklet_page_order(n) for p in pair if p >= 0]
        assert sorted(flat) == list(range(n)), f"n={n}: pages lost or duplicated"

    @pytest.mark.parametrize("n", [4, 8, 12, 16, 40])
    def test_no_blanks_when_multiple_of_four(self, n):
        flat = [p for pair in booklet_page_order(n) for p in pair]
        assert -1 not in flat

    @pytest.mark.parametrize("n", [1, 2, 3, 5, 6, 7, 17])
    def test_blanks_exactly_fill_the_padding(self, n):
        flat = [p for pair in booklet_page_order(n) for p in pair]
        assert flat.count(-1) == _padded(n) - n

    @pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6, 7, 8, 12, 16, 17, 40])
    def test_side_count_matches_padding(self, n):
        # Two pages per side, so a padded booklet has padded/2 sides.
        assert len(booklet_page_order(n)) == _padded(n) // 2

    @pytest.mark.parametrize("n", [4, 8, 12, 16, 40])
    def test_facing_pages_sum_to_a_constant(self, n):
        # The defining property of saddle-stitch: on every side the two page
        # numbers sum to padded-1. Break this and the folded booklet misreads.
        for left, right in booklet_page_order(n):
            assert left + right == _padded(n) - 1

    @pytest.mark.parametrize("n", [4, 8, 12])
    def test_outer_side_carries_first_and_last_page(self, n):
        first_side = booklet_page_order(n)[0]
        assert first_side == (n - 1, 0), "outer sheet front must be (last, first)"

    def test_sides_alternate_front_and_back(self):
        # Sides come in front/back pairs per physical sheet; the back of a sheet
        # must carry the pages adjacent to its front.
        order = booklet_page_order(8)
        assert order == [(7, 0), (1, 6), (5, 2), (3, 4)]

    def test_single_page_pads_to_one_sheet(self):
        order = booklet_page_order(1)
        assert len(order) == 2
        flat = [p for pair in order for p in pair]
        assert flat.count(0) == 1 and flat.count(-1) == 3
