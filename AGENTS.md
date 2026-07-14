# Agent rules — PressReady

## Reading ritual (start of every session)
1. AGENTS.md — this file
2. docs/ai/START_HERE.md — orientation; follow its links as the task needs

## Navigation — find code without crawling files
- Structure / "where is X?", callers, call paths → CodeGraph (`codegraph_explore` or
  `codegraph explore "..."`). Trust it; don't grep-loop.
- Intent / why / gotchas → the right file in docs/ai/ (map below).
- Do NOT hand-maintain a file map — CodeGraph owns structure.
- After editing code from WSL, run `codegraph sync` (no auto-refresh on `/mnt` — see GOTCHAS).

## docs/ai/ map
| File | Owns |
|------|------|
| START_HERE.md | Orientation, current priority, how to run |
| DESIGN_SYSTEM.md | Dark theme tokens, styling rules, overlay colors |
| DECISIONS.md | Durable "why" choices |
| GOTCHAS.md | Build/run/deploy traps, known bugs |

## Workflow
- Plan → implement → run → summarize in one go. Milestone-sized steps.
- Each change: verify (engine tests run headless in WSL; UI needs Windows Python) + a CHANGELOG.md entry.
- The engine (`pressready/engine/`) must stay Qt-free — that's what keeps it testable.

## Commit & push
- Work on `dev`; merge to `main` only on an explicit release request (then tag `vX.Y.Z`).
- Commit after each verified milestone with a real message. Push `dev` after committing.
- Stage only your own changes (`git add <paths>`, never blind `git add -A`).
- Push from WSL: `cmd.exe /c "git push origin dev"` (credentials live on the Windows side).

## Documentation upkeep
- CHANGELOG.md = what shipped (the session log; don't make a second one).
- Update DECISIONS.md on a durable choice; GOTCHAS.md when a trap is discovered.
- Keep START_HERE's "current priority" in sync with TODO.md.
