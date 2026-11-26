# Microsoft Store submission — every field, with the exact value

Paste-ready. Every technical number below is read from `AppxManifest.xml` and the installed
package, not guessed. Listing *text* (description, search terms) is in `LISTING.md`; this file
is the **Properties / requirements / configuration** side that you asked about.

The short version of "what does it need to run": **a 64-bit Windows 10/11 desktop and about
200 MB of disk. Nothing else.** It is a self-contained package — no Python, no .NET, no Qt, no
runtime to install, no internet, no configuration. That is the honest answer, and it is also a
selling point.

---

## 1. Product reservation
| Field | Value |
|-------|-------|
| Product type | **MSIX or PWA app** (so the Store signs it — not "EXE or MSI app") |
| Name | **Laydown** |

## 2. Properties page
| Field | Value |
|-------|-------|
| Category | **Productivity** |
| Subcategory | (leave blank — Productivity has none) |
| Secondary category | (optional; leave blank) |
| Privacy policy URL | See note ▼ — likely required for a full-trust app; use `https://laydown.damt.xyz/privacy/` once the page exists |
| Website | `https://laydown.damt.xyz/` |
| Support contact info | `https://github.com/danielmevit/laydown/issues` (or a support email if you prefer) |

**Product declarations** (checkboxes — all of these are **No / unchecked** for Laydown):
- Uses the Microsoft commerce platform for purchases — no (it's free)
- Depends on non-Microsoft drivers or NT services — no
- Accesses, collects, or transmits personal information — **no** (there is no network code)
- Is a screen reader / accessibility tool — no
- Uses a Bluetooth/USB peripheral — no

> **Privacy policy note.** Because the app collects nothing, a policy is *technically* not
> mandated — but the Store's certification frequently requires a URL for full-trust
> (`runFullTrust`) desktop apps regardless. Cheapest path: add a one-paragraph `/privacy` page
> to the site ("Laydown runs entirely on your device, has no network code, and collects,
> stores and transmits no personal data.") before submitting. Ask me and I'll add it in two
> minutes.

## 3. Age ratings (IARC questionnaire)
Answer **No** to everything — no violence, no user-to-user content, no data collection, no
controlled-substance/gambling references. Result: **rated for everyone (3+/E)** in all regions.

## 4. Pricing and availability
| Field | Value |
|-------|-------|
| Base price | **Free** |
| Markets | **All markets** |
| Visibility | **Public** |
| Discoverability | Available in Store, discoverable |
| Release schedule | **As soon as it passes certification** |
| Device families | **Windows 10/11 Desktop** only (the package is Desktop-targeted) |

## 5. System requirements — the real numbers
These come straight from the manifest and the installed build. In Partner Center these live under
Properties → "Minimum hardware" / "Recommended hardware" (mostly optional for desktop, but fill
them — they set buyer expectations).

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **OS** | Windows 10 version 1809 (build **17763**) | Windows 11 |
| **Architecture** | **x64 (64-bit)** only — not x86, not ARM | x64 |
| **Processor** | Any 64-bit x86-64 CPU, 1 GHz+ | Dual-core 2 GHz+ |
| **Memory (RAM)** | **4 GB** | 8 GB (for large / many-page PDFs) |
| **Free disk space** | **250 MB** (installed footprint is ~183 MB) | 500 MB |
| **Graphics** | Any; a desktop session (no headless/server core) | — |
| **Display resolution** | **1280 × 800** (the app's minimum window is 1100 × 750) | 1920 × 1080 |
| **DirectX / GPU** | Not required | Not required |
| **Internet** | **Not required** — fully offline | Not required |
| **Runtime prerequisites** | **None** — Python, Qt and PyMuPDF are bundled | None |
| **Touch** | Not required (mouse + keyboard app) | — |

**Why x64 only:** the UI is built on PyQt6, which publishes no 32-bit Windows package, so there
is no x86 build to offer (documented in `docs/ai/GOTCHAS.md`). ARM64 is technically possible
later but isn't built today.

## 6. What the package declares (auto-read from the manifest — for your reference)
The Store reads these from the uploaded `.msix`; you don't type them, but this is what it will show.

| Manifest field | Value | Meaning |
|----------------|-------|---------|
| Identity Name | `LaydownTeam.Laydown` → **replaced** by the Store identity you paste me | Package identity |
| Publisher | `CN=LaydownTeam` → **replaced** by the Store's `CN=<GUID>` | Who signs it |
| ProcessorArchitecture | `x64` | 64-bit |
| Min OS | `10.0.17763.0` | Windows 10 1809 |
| Max tested | `10.0.26100.0` | Windows 11 24H2 |
| Capability | `runFullTrust` | Ordinary desktop app (full trust). The **only** capability — no camera, mic, location, network, files-beyond-picker, etc. |
| File association | `.pdf` | Opens PDFs from Explorer |
| Entry point | `Windows.FullTrustApplication` | A packaged Win32 app |

There are **no restricted capabilities beyond `runFullTrust`**, which keeps certification simple:
the app asks for nothing sensitive.

## 7. Configuration required to run — none
There is nothing to configure. It's a self-contained MSIX:
- No .NET, Visual C++ redistributable, Python, or Qt to install — all bundled.
- No account, license key, activation, or first-run setup.
- No environment variables or config files required.
- Settings the user *chooses* (recent files, presets) are written to `HKCU\Software\Laydown` and
  a per-user config folder; nothing system-wide, nothing that needs pre-provisioning.

## 8. Packages tab
Upload `Laydown-<version>-store.msix` (unsigned — the Store signs it). One package covers x64
Windows 10 1809+ and Windows 11. On upload you'll see a **warning** (not an error):
"restricted capabilities require approval… runFullTrust". That's normal for every packaged
desktop app and does not block submission — it just needs the justification below.

## 8a. Submission Options — restricted capability justification (REQUIRED)
`runFullTrust` is a restricted capability, so the Store requires a written justification on the
**Submission Options** page. Paste this:

> Laydown is a full-trust Win32 desktop application (built with Python, PyQt6 and PyMuPDF,
> packaged as MSIX). It declares `runFullTrust` because that capability is required for any
> packaged desktop application to launch its native executable — it is not a UWP app. The
> capability is used solely to run the application's own bundled code: opening a PDF the user
> selects from local disk, arranging its pages for printing, and writing a new PDF to a location
> the user chooses. Laydown makes no network connections, installs no services or drivers, and
> accesses no data beyond the files the user explicitly opens and saves.

A human tester reviews this, which can add a little time to certification, but it is routinely
approved for genuine desktop tools. (You do **not** need this for sideloading — only for the
Store.)

## 9. Store listing (text + images)
All the wording — description, short description, the 7 search terms, "what's new" — is in
`docs/store/LISTING.md`. Screenshot: `assets/screenshot.png` (1600 × 980, meets the ≥768px rule).

---

## What I still need from you
Three values from **Partner Center → your product → Product management → Product identity**:
1. `LAYDOWN_STORE_IDENTITY_NAME` — e.g. `12345DanielMevit.Laydown`
2. `LAYDOWN_STORE_PUBLISHER` — e.g. `CN=A1B2C3D4-1234-...`
3. `LAYDOWN_STORE_PUBLISHER_DISPLAY` — your publisher display name

Paste those three and I build the Store `.msix` you upload on the Packages tab.
