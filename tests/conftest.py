"""Pytest fixtures. The bench-harness machinery itself lives in tests/helpers.py."""

import pytest

from tests.helpers import make_source_pdf


@pytest.fixture
def source_pdf(tmp_path):
    """Factory: build a source PDF in a temp dir with any shape the test needs."""
    def _make(name: str = "src.pdf", **kw) -> str:
        return make_source_pdf(str(tmp_path / name), **kw)
    return _make


@pytest.fixture
def out_path(tmp_path):
    """Factory: a path for an output PDF inside the test's temp dir."""
    def _p(name: str = "out.pdf") -> str:
        return str(tmp_path / name)
    return _p
