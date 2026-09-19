# Temporal Civic Jurisdiction Digital Twin — "who is responsible here, right now?"

> HackMysuru 1.0 · Phase 1 · Civic Governance & Clean Mysuru
> Team `<Team Name>` (`<Team ID>`)

| 📎 Submission links | 📋 Templates | 🏗️ Architecture | 🛡️ Hard constraints | ⚙️ Setup | 🤖 AI usage | ⚠️ Limitations |
|---|---|---|---|---|---|---|
| [resource.md](./resource.md) | [resource-templates/](./resource-templates/) | [docs/architecture.md](./docs/architecture.md) | [docs/constraints.md](./docs/constraints.md) | [docs/setup.md](./docs/setup.md) | [ai.md](./ai.md) | [docs/limitations.md](./docs/limitations.md) |

> Chosen sub-problem: **Routing**. Demo script for judges: [DEMO.md](./DEMO.md).

---

## 1. Problem Understanding

**Chosen sub-problem:** Routing

- **The gap we saw:** Civic authority in Indian cities is fragmented *and*
  date-sensitive — ward boundaries get delimitated, authorities get
  reorganized, and routing rules change over time. Most civic apps assume a
  **static** map, so a citizen or official asking "who is responsible here, for
  this issue, right now?" gets a wrong or stale answer.
- **Why it matters:** a mis-routed complaint is a delayed or bounced complaint —
  a blocked drain, a garbage pile-up or a pothole stays unfixed, trust in civic
  reporting drops, and in the worst cases the health or safety risk stretches
  on because no office ever owned it.
- **Why we chose this over the others:** without a trustworthy routing answer,
  every other loop (follow-through, visibility, verification) inherits the same
  mis-assignment. Fix the routing decision — deterministically and
  explainably — and the rest of the civic loop can build on solid answers.
- **What "solved" looks like for us:** a citizen never has to pick an office:
  one coordinate + issue + date is enough to know exactly which authority,
  department and service must act, what the matched rule was, and who was
  responsible *last year* or under a *proposed* boundary — all read-only and
  reproducible.

## 2. Target Users & Mysuru Context

| User | Their situation | What they need from us |
|---|---|---|
| Resident in a ward (e.g. at the MCC–panchayat edge) | No idea which office owns the drain; reporting apps give stale/bounced answers | Submit location + issue once, see who owns it and which rule matched — no picking an office |
| MCC / MUDA / PWD / CESC / NHAI officer | Disputes boundaries, inherited complaints, boundary delimiters change over time | One bounded, date-stamped answer with the in-force jurisdiction version + explanation and audit trail |
| Civic administrator / planner | Town changes (delimitation, rezone) ripple into who owns open complaints | Replay what changed historically and *preview* (read-only) what a boundary change would do before applying it |

**Local context we designed for:** fragmented multi-authority Mysuru (MCC,
MUDA, PWD, CESC, NHAI), boundary versions that flip on a calendar date,
patchy connectivity and basic Android devices — so most pages stay offline-ready
SVG maps, geolocation is one-shot and privacy-safe, and everything works on a
plain HTTP stack with no external/paid APIs.

## 3. Solution Overview

A **deterministic, explainable digital twin** that treats jurisdiction as
versioned temporal data and decides responsibility as a pure function:

```
ResponsibleEntity = f(latitude, longitude, issue_type, date,
                      jurisdiction_version, responsibility_rules)
```

Boundaries are **never overwritten**: every delimitation inserts a new row and
records a transition, so past versions stay queryable forever. That single
design decision turns "when did responsibility change here?" from an unsolved
question into an index lookup, and every what-if / migration / conflict
analysis stays **provably read-only and deterministic**.

**Core flow:**
1. A citizen (or official) picks a location (map, GPS, or manual coordinates),
   an issue and a date.
2. The temporal engine finds the in-force jurisdiction version and the routing
   table matches the authority → department → service chain, with an
   explanation + escalation path.
3. The same decision is reused to replay history, simulate proposed boundaries,
   preview complaint migrations and surface responsibility conflicts.
4. The citizen sees *who acts and why*, the officer sees a date-stamped,
   auditable answer — identical inputs always produce identical output.

**Screenshots:** `docs/images/` (2–4 images, each < 1 MB, to be added).

**Status:** P0 foundations → P9 location + mobile all shipped, tested (backend
pytest 158 test functions; `tsc --noEmit` + `vite build` on frontend), and
wired through one 8-page web app.

## 4. Architecture

"React SPA → FastAPI REST → SQLAlchemy/SQLite temporal store, with routing and
GIS behind a single `GeometryProvider` interface so the demo Shapely engine
swaps for PostGIS with one config flag."

➡️ System diagram, request walkthrough, components, 19-table data model,
APIs and tech-stack rationale: **[docs/architecture.md](./docs/architecture.md)**

## 5. Tech Stack & AI Usage

**Stack:** React 18 + TypeScript 5 + Vite 5 (Leaflet/OSM + SVG maps) ·
FastAPI + Pydantic v2 · SQLAlchemy 2 + SQLite · Shapely 2 via `GeometryProvider`
(full rationale in [docs/architecture.md](./docs/architecture.md#tech-stack))

**AI tools used in development:** Yes — AI coding assistants for scaffolding
typed API clients, React pages/components and tests; the temporal/GIS/routing
core was reviewed by hand. Full disclosure: **[ai.md](./ai.md)**

**AI inside the product:** **None** — every decision is a pure, deterministic
function; no models, no LLM calls, no external AI APIs.

## 6. Decision Log (Summary)

- **Chose:** versioned, append-only jurisdiction rows with closed-open
  `[effective_from, effective_to)` windows, **over:** overwriting a single
  "current" boundary table / static maps, **because:** past versions stay
  queryable, so history replay, what-ifs and "who was responsible last year?"
  become index lookups instead of reconstructions.
- **Chose:** a `GeometryProvider` abstraction with a Shapely/SQLite demo
  implementation, **over:** hard-coding PostGIS SQL everywhere, **because:** the
  demo runs zero-setup and offline today, and PostGIS swaps in behind the same
  interface without touching business logic.
- **First thing to break at city scale:** in-Python point-in-polygon over every
  jurisdiction row per lookup — fine for 21 synthetic jurisdictions, but a full
  Mysuru run (~400+ wards × versions) needs the PostGIS/PostgreSQL engine with
  GiST indexes (see [docs/limitations.md](./docs/limitations.md#scaling-to-all-of-mysuru)).

➡️ Full decision log: **[resource.md](./resource.md#4-submission-artifacts-google-drive)**

## 7. Setup & Run

```bash
git clone https://github.com/omkarshirol4-cloud/HM.git && cd HM
# backend:  python -m venv .venv && .venv\Scripts\python -m pip install -r requirements.txt
#           .venv\Scripts\python -m uvicorn app.main:app --port 8011   (from backend/)
# frontend: npm install && npm run dev                                  (from frontend/)
```

Open http://localhost:5173 — the backend seeds deterministic demo data on first
start (no external services, no secrets). Docker alternative:
`docker compose up --build` → frontend http://localhost:8080, backend
http://localhost:8000.

➡️ Prerequisites, environment variables, seed data, tests and troubleshooting:
**[docs/setup.md](./docs/setup.md)**

## 8. Known Limitations

- Boundary, ward and routing data are **synthetic** — a deterministic
  Mysuru-scale demo (9 wards, 3 boundary versions, 25 rules), not official
  Mysuru boundaries.
- **Applying** a what-if scenario to the live boundary set (and the conflict
  review workflow) is not implemented — migration is a read-only preview by
  design.
- The routing map's OSM base tiles need a network connection (overlays and
  manual coordinate entry work offline); browser geolocation needs a secure
  context.

➡️ Full list, edge cases and scaling roadmap:
**[docs/limitations.md](./docs/limitations.md)**

---

## Team

| Name | Role | GitHub |
|---|---|---|
| `Omkar` ⚠️ confirm | `<backend + routing engine / team lead>` | `@omkarshirol4-cloud` |
| `<name>` | `<role>` | `@<handle>` |

## License

`None declared yet — MIT recommended before submission` (no LICENSE file committed
yet; you retain full ownership of your code).