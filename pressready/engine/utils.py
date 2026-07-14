"""Unit conversions and page range parsing."""

import re
from enum import Enum
from typing import List

PT_PER_MM = 72.0 / 25.4  # ~2.8346


def mm_to_pt(mm: float) -> float:
    """Convert millimeters to PDF points."""
    return mm * PT_PER_MM


def pt_to_mm(pt: float) -> float:
    """Convert PDF points to millimeters."""
    return pt / PT_PER_MM


def inch_to_pt(inch: float) -> float:
    """Convert inches to PDF points."""
    return inch * 72.0


class Unit(Enum):
    """
    A display unit. The model always stores millimetres; this only changes what the
    operator types and reads, so a shop that thinks in inches never has to convert.
    """
    MM = "mm"
    CM = "cm"
    INCH = "in"
    POINT = "pt"

    @property
    def per_mm(self) -> float:
        return {
            Unit.MM: 1.0,
            Unit.CM: 0.1,
            Unit.INCH: 1.0 / 25.4,
            Unit.POINT: PT_PER_MM,
        }[self]

    @property
    def decimals(self) -> int:
        """Enough precision to express a useful step without noise."""
        return {Unit.MM: 1, Unit.CM: 2, Unit.INCH: 3, Unit.POINT: 1}[self]

    @property
    def step(self) -> float:
        return {Unit.MM: 0.5, Unit.CM: 0.1, Unit.INCH: 0.05, Unit.POINT: 1.0}[self]

    def from_mm(self, mm: float) -> float:
        return mm * self.per_mm

    def to_mm(self, value: float) -> float:
        return value / self.per_mm

    @property
    def suffix(self) -> str:
        return f" {self.value}"


def parse_page_range(expr: str, total_pages: int) -> List[int]:
    """
    Parse a page range expression into 0-based page indices.

    Supports: "1", "1-4", "1-4,7,10-12".  Whitespace is ignored.

    Raises ValueError on bad input.
    """
    if total_pages < 1:
        raise ValueError(f"total_pages must be >= 1, got {total_pages}")

    expr = re.sub(r"\s+", "", expr)
    if not expr:
        raise ValueError("Page range expression cannot be empty")

    result: List[int] = []
    for part in expr.split(","):
        if not part:
            continue
        if "-" in part:
            pieces = part.split("-")
            if len(pieces) != 2:
                raise ValueError(f"Invalid range: '{part}'")
            try:
                start, end = int(pieces[0]), int(pieces[1])
            except ValueError:
                raise ValueError(f"Invalid page numbers in range: '{part}'")
            if start < 1:
                raise ValueError(f"Page number must be >= 1, got {start}")
            if end > total_pages:
                raise ValueError(f"Page {end} exceeds document ({total_pages} pages)")
            if start > end:
                raise ValueError(f"Invalid range: {start} > {end}")
            result.extend(range(start - 1, end))
        else:
            try:
                page = int(part)
            except ValueError:
                raise ValueError(f"Invalid page number: '{part}'")
            if page < 1:
                raise ValueError(f"Page number must be >= 1, got {page}")
            if page > total_pages:
                raise ValueError(f"Page {page} exceeds document ({total_pages} pages)")
            result.append(page - 1)

    if not result:
        raise ValueError("No valid pages in expression")
    return result
