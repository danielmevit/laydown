"""
In-app help, generated from the schema.

The 0.2.0 tutorial documented Signatures and Page Creep as working features while
the engine ignored both — a hand-written page describing a hand-written UI, with
nothing keeping the two honest. The control reference is now derived from
``ui/schema.SCHEMA``, so it cannot describe a control that doesn't exist, and the
capability test already guarantees no control describes a setting the engine ignores.
"""

from html import escape

from pressready import __version__
from pressready.ui import theme as t
from pressready.ui.schema import SCHEMA, ControlType


def _control_rows(section) -> str:
    rows = []
    for control in section.controls:
        if control.type is ControlType.COLLECTION:
            what = "Add, remove and configure items in this list."
        else:
            what = control.description or ""
            if control.options:
                choices = ", ".join(escape(str(text)) for _, text in control.options)
                what = f"{what} <i>Choices: {choices}.</i>" if what else f"Choices: {choices}."
        rows.append(
            f"<tr><td><b>{escape(control.label)}</b></td><td>{what}</td></tr>"
        )
    return "".join(rows)


def _schema_reference() -> str:
    blocks = []
    for tab in SCHEMA:
        blocks.append(f"<h2>{escape(tab.name)}</h2>")
        for section in tab.sections:
            blocks.append(
                f"<h3>{escape(section.title)}</h3>"
                f"<p class='entity'>Controls {escape(section.entity)}.</p>"
                f"<table><tr><th>Setting</th><th>What it does</th></tr>"
                f"{_control_rows(section)}</table>"
            )
    return "".join(blocks)


def tutorials_html() -> str:
    return f"""<html><head><style>
body {{ font-family:'{t.FONT_FAMILY}',sans-serif; padding:16px; color:{t.FG}; background:{t.BG}; }}
h1 {{ color:{t.ACCENT}; border-bottom:2px solid {t.ACCENT}; padding-bottom:6px; }}
h2 {{ color:{t.ACCENT}; margin-top:26px; }}
h3 {{ color:{t.FG}; margin-top:18px; margin-bottom:2px; }}
p.entity {{ color:{t.FG_FAINT}; margin-top:0; font-size:12px; }}
code {{ background:{t.INPUT_BG}; padding:2px 6px; border-radius:3px; color:{t.FG}; }}
table {{ border-collapse:collapse; margin:8px 0 16px 0; width:100%; }}
td, th {{ border:1px solid {t.BORDER}; padding:6px 10px; text-align:left;
          vertical-align:top; }}
th {{ background:{t.RAISED}; color:{t.ACCENT}; }}
i {{ color:{t.FG_MUTED}; }}
.tip {{ background:{t.RAISED}; border-left:3px solid {t.ACCENT}; padding:8px 12px; margin:12px 0; }}
</style></head><body>

<h1>PressReady {escape(__version__)}</h1>
<p>Lay source pages out on press sheets. Imposition is vector — pages are embedded,
never rasterized, so output quality always matches the source.</p>

<h2>Getting started</h2>
<p><b>File → Open PDF</b> (Ctrl+O), or drag a PDF onto the window. The canvas shows every
imposed sheet exactly as it will print. Click <b style="color:{t.ACCENT}">Generate PDF</b>
(Ctrl+G) to export.</p>
<div class="tip"><b>The preview is the output.</b> Sheets are rendered from a real
imposition, and the magenta outlines are the cut lines that run actually used — not a
separate drawing that might disagree.</div>

<h2>Bleed and boxes</h2>
<p>A press-ready PDF marks its finished page with a <b>trim box</b> and paints artwork past
it to a <b>bleed box</b>. PressReady imposes the trim box by default, so what lands on the
cell is the finished page. Files without boxes are unaffected: PDF makes the trim box fall
back to the whole page. Set a <b>bleed</b> under Source to carry artwork past the cut line
so a slightly off cut still lands on ink.</p>

{_schema_reference()}

<h2>View overlays</h2>
<table>
<tr><th>Toggle</th><th>Shortcut</th><th>Shows</th></tr>
<tr><td>Page Numbers</td><td>Alt+1</td><td>Which source page sits in each cell</td></tr>
<tr><td>Cut Lines</td><td>Alt+2</td><td>Where each page will be trimmed</td></tr>
<tr><td>Page Tops</td><td>Alt+3</td><td>Which edge is the top — check rotation</td></tr>
<tr><td>Page Previews</td><td>Alt+4</td><td>The page content itself</td></tr>
</table>

<h2>Presets</h2>
<p><b>File → Save Preset</b> writes every setting to a small JSON file;
<b>Load Preset</b> restores it. Handy for a recurring job.</p>

<h2>Keyboard</h2>
<table>
<tr><td>Ctrl+O</td><td>Open PDF</td></tr>
<tr><td>Ctrl+G</td><td>Generate PDF</td></tr>
<tr><td>Ctrl+Z / Ctrl+Y</td><td>Undo / redo a setting</td></tr>
<tr><td>Ctrl++ / Ctrl+-</td><td>Zoom in / out</td></tr>
<tr><td>Ctrl+0</td><td>Fit to width</td></tr>
<tr><td>Ctrl+F4</td><td>Close PDF</td></tr>
<tr><td>F1</td><td>This page</td></tr>
</table>
</body></html>
"""
