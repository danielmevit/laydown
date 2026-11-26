# Laydown — Handoff

Everything a person (or agent) needs to pick this project up. For *why* the code is built the
way it is, read `AGENTS.md` then `docs/ai/START_HERE.md`; this file is the operational state —
what's shipped, what's pending, and how to move each piece forward.

_Last updated: 2026-10-15, at version 0.4.7._

---

## 1. Status at a glance

| Thing | State |
|-------|-------|
| **What it is** | Laydown — a desktop app for **PDF imposition** (laying source pages onto press sheets). Python + PyQt6 UI + PyMuPDF engine. |
| **Current version** | **0.4.7** (`laydown/__init__.py` is the single source of truth) |
| **Repo** | <https://github.com/danielmevit/laydown> (default branch `main`; work on `dev`, merge to `main` on release) |
| **Website** | <https://laydown.damt.xyz/> — Astro, in `site/`, deploys from `main` |
| **GitHub releases** | **0.4.7**, all platforms — Windows (MSIX + portable), macOS (arm64 + Intel), Linux x86_64 |
| **Microsoft Store** | **Submitted 2026-07-18, outcome UNVERIFIED as of 2026-10-12 (no public listing found).** Package version 0.4.1. See §3. |
| **Tests** | the full suite, run headless anywhere (`pytest`). CI gates every release on them. |
| **License** | AGPL-3.0-only |

The name was **PressReady** through 0.3.0; renamed to **Laydown** at 0.4.0 to avoid Fujifilm's
"Revoria XMF PressReady" (same field). Releases 0.2.0/0.3.0 keep their PressReady-named files —
that's history, don't rewrite it.

---

## 2. Distribution channel A — GitHub Releases (primary, all platforms)

This is the live, current channel. Every OS gets a direct download.

**To cut a release:** bump `laydown/__init__.py`, add a `CHANGELOG.md` entry, commit, then:

```bash
git tag -a vX.Y.Z -m "Laydown X.Y.Z ..."
git push origin vX.Y.Z        # from WSL: cmd.exe /c "git push origin vX.Y.Z"
```

The tag fires `.github/workflows/release.yml`:
- Four build jobs — Windows x64, macOS arm64 (`macos-15`), macOS Intel (`macos-15-intel`),
  Linux x86_64 — each runs the tests **and** `--smoke` before packaging.
- A single `release` job needs all four, then publishes once. **A partial release is
  impossible**: if any platform fails, nothing publishes and you re-run the job.
- The Windows MSIX is signed with the stable certificate (see §4), so updates need no re-trust.
- Build toolchain is pinned in `packaging/constraints.txt` (every CI build installs with `-c`).
  PyMuPDF floor is 1.28.0. A tag build without the `LAYDOWN_CERT_PFX_B64` secret now fails instead
  of minting a throwaway certificate. The Windows job fails if no MSIX was produced.
- **Before the next tag, dry-run the pipeline** (the pins and action majors changed on 2026-10-12):
  `gh workflow run release.yml --repo danielmevit/laydown --ref dev -f windows_only=true`, then a
  full dispatch, and check every platform built before tagging.

**Watch a run:** `gh run list --repo danielmevit/laydown` / `gh run view <id>`.

**Known:** there is no 32-bit Windows build — PyQt6 ships no `win32` wheel (see `docs/ai/GOTCHAS.md`).

---

## 3. Distribution channel B — Microsoft Store (Windows) — **STATUS UNVERIFIED (owner: check Partner Center)**

Submitted **2026-07-18**. As of 2026-10-12 the outcome is **UNVERIFIED** (no public listing
found). The owner must check Partner Center. Certification for a full-trust app can take longer
than the usual 1–3 days because a human reviews the `runFullTrust` justification.

### The submission, as filed
- **Product name:** Laydown (reserved as an **MSIX or PWA app**)
- **Package identity** (from Partner Center → Product management → Product identity):
  - `Package/Identity/Name` = **`Mevit.Laydown`**
  - `Package/Identity/Publisher` = **`CN=FC84DC20-8F99-4304-B4A8-3C0DA3D25EF4`**
  - `PublisherDisplayName` = **`Mevit`**
  - Package Family Name = `Mevit.Laydown_mgh9atdt90ne4` (a *derived* value; the suffix is the
    hash of the Publisher — verified it matches the package we built)
- **Package uploaded:** `Laydown-0.4.1-store.msix` — **unsigned** (the Store signs it), version
  0.4.1.0, x64, min Windows 10 1809. This passed acceptance validation.
- **runFullTrust:** a restricted-capability **warning** (not an error). The justification was
  provided on the Submission Options page; the text is in `docs/store/SUBMISSION.md` §8a.
- **Listing / Properties / Privacy / Age rating:** all filled from `docs/store/LISTING.md` and
  `docs/store/SUBMISSION.md`. Privacy policy URL: <https://laydown.damt.xyz/privacy/>
  (live). Age rating: everyone. Price: free, all markets.

### What to do when the review comes back
- **If approved:** it goes live; `winget install Laydown` then works automatically via the Store
  source, and Windows users get one-click install with **no certificate step**.
- **If it asks a question** (most likely about runFullTrust): the justification in
  `docs/store/SUBMISSION.md` §8a is the standard, accepted answer — reply with that.
- **The Store is behind GitHub** (Store = 0.4.6 "Laydown - Print Layouts" submitted 2026-10-14, GitHub = 0.4.7). This is fine — they're
  independent channels. **After the 0.4.1 review clears, submit a Store update to catch up:**
  build the current version's Store package (§below) and upload it as a new submission. Don't
  update the package *while* the current one is in review, or review restarts.

### Building the Store package (unsigned, stamped with the Store identity)
Run the on-demand workflow with the three identity values (they're public, passed as inputs):

```bash
gh workflow run "Store package" --repo DanielMevit/laydown --ref main \
  -f identity_name="Mevit.Laydown" \
  -f publisher="CN=FC84DC20-8F99-4304-B4A8-3C0DA3D25EF4" \
  -f publisher_display="Mevit"
```

It builds `Laydown-<version>-store.msix` as a workflow artifact. Download it, verify identity +
that it's unsigned (see the checks in the commit history around the first Store build), and upload
on the Partner Center Packages tab. `.github/workflows/store.yml` and `packaging/windows/build.ps1
-Store` are the machinery.

---

## 4. Code signing — the certificate (read before touching releases)

The GitHub-release MSIX is self-signed. **It must use the same certificate every release**, or
users have to re-trust on each update.

- The stable cert lives in **repo secrets** `LAYDOWN_CERT_PFX_B64` / `LAYDOWN_CERT_PASSWORD`
  (created 2026-07-16, `CN=LaydownTeam`, thumbprint **`2D87584C...`**, expires 2031). A private
  copy is in local `certs/` (gitignored — treat it as the backup of the key).
- `release.yml` restores it before building; `build.ps1` signs with it and ships the public half
  as `Laydown-msix-signing.cer` beside the installer.
- **A user installs the MSIX once with:** trust `Laydown-msix-signing.cer` into
  `LocalMachine\TrustedPeople` (elevated PowerShell), then `Add-AppxPackage`. One-time; future
  releases share the cert. The exact commands are in the release notes and `README.md`.
- **History / lesson:** the *first* 0.4.x MSIX (and 0.3.0) failed with `0x800B010A` because CI
  minted a throwaway cert per run — the public cert users needed died with the runner. That's why
  the cert is now a stable secret. Don't go back to per-run certs.
- **The subject must equal the manifest `Publisher`.** The rename forced a new cert (the old
  PressReady one signs nothing now). If you rebrand again, mint a new cert to match.

The **Store** package is different: it's *unsigned* (Microsoft signs it) and carries the Store
identity, not `CN=LaydownTeam`. Don't sign the Store package.

---

## 5. Local development

```bash
pip install -e ".[dev]"        # PyQt6 + PyMuPDF + pytest
python -m laydown              # run the app (needs a desktop session)
python -m laydown --smoke      # headless end-to-end self-check, exits 0/1
python -m laydown impose SRC.pdf -o OUT.pdf [--preset P.json] [--set TARGET=VALUE ...] [--force]  # headless CLI
python -m laydown preflight SRC.pdf [--preset ...] [--set ...] [--json]  # headless preflight, exit 0/1/2
pytest                         # the full suite, no display needed
```

- **WSL note:** the venv is `~/.venvs/laydown` (D: has no room). The GUI *shows* only on a real
  desktop, but the window can be *constructed* headless (`QT_QPA_PLATFORM=offscreen`), which is how
  `--smoke` and the UI tests run. Screenshots for review are grabbed offscreen the same way.
- **Pushing from WSL:** credentials live on the Windows side — `cmd.exe /c "git push origin dev"`.
- **CodeGraph:** run `codegraph sync` after edits (no auto-watch on `/mnt`).

---

## 6. The map (where deeper docs live)

| File | What it holds |
|------|---------------|
| `AGENTS.md` | The operating rules + doc map. Read first. |
| `docs/ai/START_HERE.md` | Orientation, current priority, how to run |
| `docs/ai/DECISIONS.md` | *Why* choices were made (rename, no-32-bit, engine/UI contract…) |
| `docs/ai/GOTCHAS.md` | Every trap that cost time — PowerShell ASCII, runner-label retirement, the cert, `setParent(None)`, Qt palette, … |
| `docs/ai/REFERENCE_STUDY.md` | What Imposition Wizard 3 and Toolcraft taught the design |
| `docs/store/LISTING.md` | Paste-ready Store listing text |
| `docs/store/SUBMISSION.md` | Every Store field with the exact value + the runFullTrust justification |
| `ROADMAP.md` | Done / backlog / not-doing |
| `CHANGELOG.md` | What shipped, per version |

**Two rules the tests enforce, so you can't break them by accident:**
1. A control the engine doesn't honour can't exist in the UI (`engine/capabilities.py` + tests).
2. Settings UI is declared in `ui/schema.py`, never hand-built.

---

## 7. Open items / what's next

- **Microsoft Store review** — waiting (§3). When it lands, react per §3.
- **Store version catch-up** — after 0.4.1 approves, submit a 0.4.6+ Store update.
- **ROADMAP backlog** — Step & Repeat / Cut Stack layouts, a headless CLI (the engine is already
  Qt-free for it), more marks/units. Work-and-turn/tumble stays out until a pressman validates it.
- **Signing** — the self-signed model means a one-time trust step per user on the GitHub MSIX. A
  paid code-signing cert (or the Store, once live) removes it. Not urgent.
