# HackMysuru 1.0 — Phase 1 Submission Index

> **This is the landing file for the submission.** Every evaluation artifact is
> uploaded to Google Drive and linked below. Any artifact not linked here before
> the freeze (20 September 2026, 23:59 IST) does not exist for judging.

<!-- HOW TO FILL
1. Replace every <placeholder> before the freeze. These HTML comments can be deleted.
2. Use a PERSONAL Gmail account for uploads (college Workspace often blocks
   "Anyone with the link").
3. Share each FILE as General access → "Anyone with the link" → Viewer.
4. Test every link in an incognito/private window before the deadline.
-->

---

## 1. Team Details

| Field | Value |
|---|---|
| Team ID (from dashboard) | `<HM1-XXXX>` |
| Team Name | `<team name>` |
| College(s) | `<college name(s)>` |
| Team Leader | `<name>` · `<email>` · `<phone>` |
| Repository | https://github.com/omkarshirol4-cloud/HM |

| # | Member | Program & Year | GitHub Handle | Primary Role |
|---|---|---|---|---|
| 1 | `Omkar` (Lead) ⚠️ confirm | `<B.E. CSE, 3rd yr>` | `@omkarshirol4-cloud` | `<backend + routing engine>` |
| 2 | `<name>` | `<...>` | `@<handle>` | `<frontend / GIS / ...>` |
| 3 | `<name>` | `<...>` | `@<handle>` | `<...>` |
| 4 | `<name>` | `<...>` | `@<handle>` | `<...>` |

## 2. What We Built (one-liner)

**Sub-problem:** Routing

**In one sentence:** A temporal digital twin that answers "who is responsible
here, for this issue, right now?" as a deterministic function of location +
issue + date over versioned (never-overwritten) jurisdiction boundaries and
routing rules — and replays history, simulates boundary changes and previews
migrations all from that one decision.

## 3. Repository Documents

| Document | What it covers |
|---|---|
| [README.md](./README.md) | Problem, users, solution overview, links to everything below |
| [ai.md](./ai.md) | AI tools used in development and AI/ML inside the product |
| [docs/architecture.md](./docs/architecture.md) | System diagram, components, data model (19 tables), APIs, tech stack |
| [docs/constraints.md](./docs/constraints.md) | How we handle the hard constraints (temporal jurisdiction, conflicts, determinism, read-only analysis) |
| [docs/setup.md](./docs/setup.md) | Local setup, seed data, tests, Docker, troubleshooting |
| [docs/limitations.md](./docs/limitations.md) | Known gaps, edge cases, scaling roadmap |
| [DEMO.md](./DEMO.md) | 3–5 minute judge walkthrough + failover cheat-sheet |

## 4. Submission Artifacts (Google Drive)

| # | Artifact | Google Drive Link | File Name | SHA-256 (first 16 chars) |
|---|---|---|---|---|
| 1 | Pitch + Code Walkthrough Video (≤ 10 min, MP4) | `<https://drive.google.com/file/d/.../view>` | `<TeamID>_video.mp4` | `<a1b2c3d4e5f60718>` |
| 2 | Decision Log (1 page, PDF) | `<https://drive.google.com/file/d/.../view>` | `<TeamID>_decision-log.pdf` | `<...>` |
| 3 | Presentation (≤ 10 slides, PDF) | `<https://drive.google.com/file/d/.../view>` | `<TeamID>_presentation.pdf` | `<...>` |

```
Windows SHA-256:  certutil -hashfile <file> SHA256   → paste first 16 chars
macOS / Linux:    shasum -a 256 <file> (or sha256sum <file>)
```

### Video Chapters (match the ≤ 10 min template)

| Timestamp | Section |
|---|---|
| `00:00` | Part 1: Problem & target users |
| `00:40` | Part 1: Live demo — flip point `(76.607313, 12.279256)` on Citizen Routing |
| `01:50` | Part 1: Bad-input / offline handling (tiles fallback, NO_JURISDICTION states) |
| `02:30` | Part 1: Historical Replay — boundary change across DELIM-2020 → DELIM-2024 |
| `03:00` | Part 2: Architecture overview (FastAPI → services → GeometryProvider, React) |
| `04:30` | Part 2: Data model & temporal API (`/gis/lookup`, `/routing/resolve`, `/replay/point`) |
| `05:30` | Part 2: Key code walkthrough (temporal engine + routing decision) |
| `07:30` | Part 2: Decisions & trade-offs (never-overwrite, SpatiaLite→PostGIS, rules engine) |
| `08:30` | Part 2: Scaling & limitations |
| `09:15` | Part 2: AI usage (see [ai.md](./ai.md)) |

## 5. Live MVP

| Field | Value |
|---|---|
| Live URL | `<https://... — currently runs locally / Docker only: http://localhost:5173>` |
| Platform | Web (React SPA, mobile-first, PWA-ready) |
| Test login (if any) | None — no auth at the citizen level; admin token via `TCIVIC_ADMIN_TOKEN` |
| Sample data loaded? | Yes — deterministic synthetic Mysuru-scale seed (9 wards, 3 boundary versions, 25 routing rules, 9 complaints) |
| How to test offline mode | Open the app, then Chrome DevTools → Network → Offline: the civic overlays still render; OSM tiles show the in-app "tiles unavailable (offline?)" notice. Full steps in [docs/setup.md](./docs/setup.md) |
| If the live link is down | Follow [docs/setup.md](./docs/setup.md) — ~2 commands, fully offline, no external services |

## 6. Quick Reviewer Path (≤ 3 minutes)

1. Start: Dashboard → **Start Demo** → Citizen Routing.
2. Tap the quick flip **"Garbage collection · V1/V2 flip"** → the result resolves
   on 2024-06-01 to **W-01 · DELIM-2024 · MCC Health & Sanitation · SVC-GARBAGE ·
   RULE-GARBAGE-01** with an explanation and audit id.
3. **"Explore this location historically →"** → Replay shows 3 periods / 2 boundary
   changes (`DELIM-2020` rule → `(no jurisdiction)` gap → `DELIM-2024` rule).
4. **What-If Simulator** → "Heritage expansion · inside rezone" → **Simulate**
   (read-only before/after cards).
5. **Responsibility Graph** → the default heritage chain `Location →
   JURISDICTION → AUTHORITY → DEPARTMENT → SERVICE → ISSUE → ESCALATION`.

## 7. Declaration

- [ ] All Drive links open in an incognito window with **Viewer** access (no "Request access").
- [ ] The video is one continuous recording, ≤ 10 minutes, Part 1 then Part 2.
- [ ] The decision log is one page and written by us in our own words.
- [ ] All AI tools used (development and in-product) are disclosed in [`ai.md`](./ai.md).
- [ ] No code specific to this challenge was written before 18 Sept 2026, 00:00 IST.
- [ ] We will not modify or replace any linked file after 20 Sept 2026, 23:59 IST.

**Submitted by:** `<Team Leader name>` · **Date/Time (IST):** `<20-09-2026 21:40>`