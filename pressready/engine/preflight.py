"""
Preflight — say what's wrong before the press does.

0.2.0 discovered problems at export: "Margins/gutters too large for sheet size"
arrived as an exception after the operator hit Generate, and subtler issues (a source
with no trim box, bleed with nowhere to go, a page count that doesn't fold) arrived
at the guillotine. Imposition Wizard has had a preflight dashboard for years; this is
the same idea sized to PressReady.

Checks are pure functions of a Project plus the source document, so they run on every
settings change without touching the UI.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

import fitz

from pressready.engine.data_model import LayoutType, Project, SourceBox
from pressready.engine.geometry import cell_grid, grid_for, source_boxes
from pressready.engine.utils import mm_to_pt, pt_to_mm


class Severity(Enum):
    ERROR = "Error"      # imposition will fail or the output is unusable
    WARNING = "Warning"  # it will produce output, but probably not what was wanted
    NOTE = "Note"        # worth knowing


@dataclass(frozen=True)
class Finding:
    severity: Severity
    message: str
    detail: str = ""

    def __str__(self) -> str:
        return f"{self.severity.value}: {self.message}"


def preflight(project: Project, source: Optional[fitz.Document] = None) -> List[Finding]:
    """
    Everything worth telling the operator about this job, worst first.

    *source* is optional so the sheet-geometry checks work with no PDF loaded.
    """
    findings: List[Finding] = []
    findings += _check_sheet(project)
    if source is not None and len(source):
        findings += _check_source(project, source)
        findings += _check_fit(project, source)
    findings.sort(key=lambda f: list(Severity).index(f.severity))
    return findings


def _check_sheet(project: Project) -> List[Finding]:
    try:
        cols, rows = grid_for(project.layout)
    except ValueError as exc:
        return [Finding(Severity.ERROR, str(exc))]

    if project.layout.layout_type == LayoutType.BOOKLET:
        cols, rows = 2, 1
    try:
        cell_grid(project, cols, rows)
    except ValueError as exc:
        return [Finding(
            Severity.ERROR, str(exc),
            "Reduce the margins or gutters, or use a larger sheet.",
        )]
    return []


def _check_source(project: Project, source: fitz.Document) -> List[Finding]:
    findings: List[Finding] = []
    page = source[0]

    if project.source.box == SourceBox.TRIM and page.trimbox == page.rect:
        findings.append(Finding(
            Severity.NOTE,
            "This PDF has no trim box, so the whole page is being imposed",
            "That is the right behaviour for an ordinary PDF. If it was exported for "
            "print and should carry a trim box, check the export settings.",
        ))

    if project.source.bleed_mm > 0:
        available = pt_to_mm(min(
            page.trimbox.x0 - page.rect.x0, page.rect.x1 - page.trimbox.x1,
            page.trimbox.y0 - page.rect.y0, page.rect.y1 - page.trimbox.y1,
        )) if page.trimbox != page.rect else 0.0
        if project.source.bleed_mm > available + 0.01:
            findings.append(Finding(
                Severity.WARNING,
                f"Asked for {project.source.bleed_mm:g} mm of bleed but the source only "
                f"carries {max(available, 0):.1f} mm",
                "The bleed is clamped to the artwork that exists, so the cut edge may "
                "run out of ink.",
            ))

    sizes = {(round(p.rect.width, 1), round(p.rect.height, 1)) for p in source}
    if len(sizes) > 1:
        findings.append(Finding(
            Severity.WARNING,
            f"The source mixes {len(sizes)} different page sizes",
            "Each page is fitted to its cell individually, so they will not line up.",
        ))
    return findings


def _check_fit(project: Project, source: fitz.Document) -> List[Finding]:
    findings: List[Finding] = []
    layout = project.layout

    if layout.layout_type == LayoutType.BOOKLET:
        count = len(source)
        if count % 4:
            findings.append(Finding(
                Severity.NOTE,
                f"{count} pages will be padded to {((count + 3) // 4) * 4} with blanks",
                "A folded sheet always carries four pages. Use 'Blanks in the middle' "
                "to keep a printed back cover.",
            ))
        cols, rows = 2, 1
    else:
        cols, rows = grid_for(layout)

    try:
        cells = cell_grid(project, cols, rows)
    except ValueError:
        return findings  # already reported by _check_sheet

    page = source[0]
    place, _ = source_boxes(page, project.source)
    cell = cells[0]

    scale = min(cell.width / place.width, cell.height / place.height)
    if layout.auto_rotate:
        scale = max(scale, min(cell.width / place.height, cell.height / place.width))

    if scale < 0.999:
        # Graded rather than shouted. Fitting A4 two-up onto A3 with any margin at all
        # lands near 97%, and that is the job this tool is *for* — warning about it
        # every time would just teach the operator to ignore the strip. A serious
        # reduction still gets a warning, and dimensional work still gets told.
        severity = Severity.WARNING if scale < 0.9 else Severity.NOTE
        findings.append(Finding(
            severity,
            f"Pages are being scaled to {scale * 100:.0f}% to fit their cell",
            "Imposition places pages at full size unless they have to shrink. A larger "
            "sheet, smaller margins, or fewer pages per sheet would keep them at 100% — "
            "which matters if the job has to hold its dimensions."
            + ("" if layout.auto_rotate else " Turning pages to fit may also help."),
        ))

    waste = 1.0 - (place.width * scale * place.height * scale) / (cell.width * cell.height)
    if 0.35 < waste < 1.0 and scale >= 0.999:
        findings.append(Finding(
            Severity.NOTE,
            f"About {waste * 100:.0f}% of each cell is empty",
            "The page proportions differ from the cell, so pages sit letterboxed.",
        ))
    return findings
