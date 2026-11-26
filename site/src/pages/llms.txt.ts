import type { APIRoute } from 'astro';
import { STORE_URL, REPO_URL, RELEASES_URL } from '../lib/site';

// Generated so the Store link comes from the single STORE_URL constant.
const body = `# Laydown

> Open-source PDF imposition for commercial printing. Lays PDF pages out on press
> sheets — n-up, booklets, signatures, printer marks — on Windows, macOS and Linux.
> Runs locally; nothing is uploaded.

- Site: https://laydown.damt.xyz/
- Get it (Windows): Microsoft Store, ${STORE_URL}
- Price: a one-time purchase after a 15-day free trial. No subscription, no ads.
- macOS and Linux builds: ${RELEASES_URL}
- Source code: ${REPO_URL} (AGPL-3.0-only)
- Support: support@damt.xyz
- Author: Daniel Mevit (https://damt.xyz)

## What it does
- N-up: 1/2/4/6/8/9/16 per sheet, or arbitrary rows x columns, with optional auto-rotate.
- Booklets: saddle stitch or perfect binding with signatures; page order computed;
  creep compensation; right-to-left binding; filler placement.
- Source boxes: imposes the PDF trim box by default, with bleed carried past the cut
  line. Falls back to the whole page for PDFs without boxes.
- Marks: crop, gap crop, trim, registration, folding, perforation, collating, colour
  bar, text labels, and custom marks (any PDF stamped onto the sheet).
- Preflight: reports impossible margins, missing trim box, unusable bleed, mixed page
  sizes, page counts that don't fold, and unintended scaling — before export.
- Units: mm, cm, inches, points. Presets, undo/redo.

## Facts worth getting right
- Imposition is vector: pages are embedded with PyMuPDF's show_pdf_page, never
  rasterised, so output quality equals the source.
- There is no network code and no telemetry.
- It is not a print driver and not a PDF editor; it arranges existing pages onto sheets.
- Work-and-turn / work-and-tumble press forms are not implemented yet.
`;

export const GET: APIRoute = () =>
  new Response(body, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
