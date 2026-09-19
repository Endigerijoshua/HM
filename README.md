# Temporal Civic Jurisdiction Digital Twin

HackMysuru 2026 · **Routing** problem statement.

## Problem statement

Civic authority in Indian cities is fragmented and date-sensitive: ward
boundaries get delimitated, authorities get reorganized and routing rules
change over time. Most civic apps assume a *static* map, so a citizen or
official asking "who is responsible here, for this issue, right now?" gets a
wrong or stale answer — and no one can answer "who was responsible last year?"
or "what changes would happen if this boundary is redrawn?".

## Solution

A **deterministic, explainable digital twin** that treats jurisdiction as
versioned temporal data and decides responsibility as a pure function:

```
ResponsibleEntity = f(latitude, longitude, issue_type, date,
                      jurisdiction_version, responsibility_rules)
```

Given a location + issue + date it returns the **authority, department and
service** that must act, with the **routing rule** that matched, the
jurisdiction version in force, an **explanation**, an escalation path and an
audit record. The same engine is also used to **replay history**, **simulate
what-if boundary changes**, **preview complaint migrations**, **detect
jurisdiction-vs-routing conflicts** and **render an explanatory
responsibility graph** — all through one web app.

## Core innovation

Boundaries are **never overwritten**. Every delimitation inserts a new row and
records a transition, so past versions stay queryable forever. This single
design decision turns "when did responsibility change here?" from an unsolved
question into an index lookup, and makes every what-if / migration / conflict
analysis provably read-only and deterministic.

## Status

P0 foundations → P8 complete frontend integration are all shipped and tested,
plus **P9 location + mobile**: browser geolocation, pick-on-map and manual
coordinate entry on Citizen Routing, and a mobile-first layout with a sidebar
drawer. The 8-page web app drives the real backend end to end (see
[Roadmap](#roadmap) for the per-phase breakdown).

---

## Why this exists

Most civic apps assume boundaries are static. In reality wards get
delimitated, authorities get reorganized, and responsibility can shift by
date. This system treats boundaries as **versioned, temporal data** and keeps
history immutable so it can later answer:

1. Who is responsible **today**?
2. Who was responsible on a **previous date**?
3. Who **would** be responsible if a boundary change were applied?
4. Which open complaints would a boundary change **affect**?
5. Are there **conflicts** between geographic jurisdiction and service rules?

---

## Architecture

```
React + TypeScript + Vite (SVG jurisdiction map on /history) [P1]
        │  JSON REST over /api/v1
        ▼
FastAPI (routers → pydantic schemas → services)
        │
        ├── SQLAlchemy · SQLite (demo)  ──────►  PostgreSQL/PostGIS (future)
        └── GeometryProvider (GIS abstraction)
              ├── ShapelyGeometryProvider (SQLite + in-Python predicates) [P0]
              └── PostGisProvider (ST_* SQL)                                [future]
```

**Key idea:** business logic talks only to the `GeometryProvider` interface.
Swapping the demo geometry engine for PostGIS later requires no changes above
the DI boundary.

## Tech stack

- **Backend:** Python 3.13 · FastAPI · SQLAlchemy · SQLite (SQLAlchemy,
  file-backed demo store) · Pydantic v2 · Shapely (geometry predicates) ·
  Uvicorn.
- **Frontend:** React 18 · TypeScript 5 · Vite 5 · react-router-dom 6 · plain
  CSS custom properties (no UI framework) · SVG vector jurisdiction map (no
  map SDK) · zero additional runtime dependencies beyond the four above.
- **Tests:** pytest (backend, in-process TestClient + live HTTP smoke) ·
  `tsc --noEmit` + `vite build` (frontend).
- **Ops:** Docker compose for a one-command demo stack (backend + nginx
  serving the static build and reverse-proxying `/api`).

### Temporal model

- Validity windows are closed-open intervals `[effective_from, effective_to)`;
  `NULL` `effective_to` means "open ended".
- Jurisdiction rows are **never mutated or deleted**. A boundary change
  inserts a new row and records a `jurisdiction_changes` transition
  (`MODIFIED`, `SUPERSEDED`, `CREATED`, …). Historical versions stay
  queryable forever.
- `jurisdiction_versions` groups coherent snapshots (e.g. `DELIM-2020`,
  `DELIM-2024`) with a `CURRENT / PROPOSED / SUPERSEDED` status.

---

## Repository layout

```
temporal-civic-dt/
├─ backend/
│  ├─ app/
│  │  ├─ api/            # routers (health, gis, routing), deps (db, provider, routing, admin guard)
│  │  ├─ core/           # errors (structured envelope), reference IDs
│  │  ├─ config.py       # pydantic-settings (TCIVIC_* env vars)
│  │  ├─ db/             # engine/session + SQLAlchemy models (19 tables)
│  │  ├─ gis/            # provider ABC + CRS + ops + temporal engine + Shapely impl
│  │  ├─ main.py         # FastAPI app + lifespan (create tables + seed)
│  │  ├─ routing/        # P2 responsibility routing service
│  │  ├─ schemas/        # pydantic request/response models (incl. schemas/gis.py, schemas/routing.py)
│  │  ├─ seed/           # deterministic Mysuru-style demo data (incl. P2 issue types + routing rules)
│  │  └─ logging_config.py
│  ├─ tests/             # pytest suite (P0 + P1 GIS + P2 routing: 158 tests)
│  ├─ requirements.txt
│  ├─ .env.example
│  └─ Dockerfile
├─ frontend/
│  ├─ src/
│  │  ├─ api/            # typed client (fetch), ApiError, health + GIS types/client
│  │  ├─ components/     # app shell, sidebar, placeholder, SVG JurisdictionMap
│  │  ├─ pages/          # dashboard + 7 module pages (Historical Explorer built)
│  │  ├─ App.tsx         # routes
│  │  └─ index.css
│  ├─ vite.config.ts     # dev proxy /api → backend
│  ├─ Dockerfile + nginx.conf
├─ docker-compose.yml
└─ README.md
```

---

## Running locally

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8011
```

On startup the app creates the tables (SQLite) and seeds deterministic demo
data. Open http://127.0.0.1:8011/docs for the interactive API. Port **8011** is
the development backend the frontend proxy targets by default.

Health check: `GET /api/v1/health`

### Frontend (dev)

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite proxies every `/api/*` request to the backend
(default `http://127.0.0.1:8011`), so the browser only talks to the Vite server
and the backend never sees CORS.

Backend connection is configured entirely by environment variables (never
hard-coded in components):

- `VITE_API_BASE_URL` — API base path (default `/api/v1`). Leave as-is when
  using the Vite proxy or the bundled nginx reverse proxy. Set it to an
  absolute URL (e.g. `http://127.0.0.1:8011/api/v1`) only if you bypass the
  proxy.
- `VITE_DEV_PROXY_TARGET` — dev-server proxy target (default
  `http://127.0.0.1:8011`). Override when the backend runs on another port:

```powershell
$env:VITE_DEV_PROXY_TARGET="http://localhost:8010"; npm run dev
```

Copy `frontend/.env.example` to `frontend/.env` to persist overrides. The
dashboard card and the sidebar dot both surface backend health via
`GET /api/v1/health`.

### Tests

```powershell
cd backend
.venv\Scripts\python -m pytest -q   # 168 tests, all passing (exit 0)
```

Frontend static checks: `npm run typecheck` / `npm run build`.

### Docker

```powershell
docker compose up --build
```

- Backend → http://localhost:8000
- Frontend (nginx) → http://localhost:8080

The compose file mounts a named volume so the SQLite database survives
restarts. No external or paid APIs are used anywhere.

---

## Demo flow (the judge walkthrough)

The app is built as one continuous story — every step feeds the next, and
every page reads live backend data:

1. **Dashboard** — health indicator, the core formula
   *Responsible Entity = Location + Issue + Date + Version + Rules*, the
   responsibility pipeline and the 7 implemented modules. **Start Demo**
   drops into Citizen Routing.
2. **Citizen Routing** — click a quick flip or the map, then pick date/issue:
   the engine returns jurisdiction, authority, department, service, matched
   rule and explanation. "Explore this location historically" carries the same
   coordinate into Historical Replay; "Open in Historical Explorer" into the map.
3. **Historical Explorer / Replay** — slide the date to watch the same
   coordinate change jurisdiction across `DELIM-2020` → gap →
   `DELIM-2024`; Replay renders the timeline with explicit **BOUNDARY CHANGE**
   markers.
4. **What-If Simulator** — pick the proposed rezone: before/after boundary
   cards, impact metrics, affected complaints and potential conflicts under a
   **SIMULATION ONLY · NO LIVE DATA MODIFIED** ribbon.
5. **Complaint Migration** — the 3 complaints that must migrate, shown
   `OLD → NEW` (jurisdiction/authority/department/service) as a **READ-ONLY
   PREVIEW**.
6. **Responsibility Conflicts** — the detector's persisted findings
   (e.g. `GEO_VS_SERVICE`) with severity and status.
7. **Responsibility Graph** — the same point renders `Location →
   Jurisdiction → Authority → Department → Service → Issue → Escalation`.

## Demo / seed data (synthetic)

The seed is deterministic (fixed RNG seeds) and fully offline. It generates
a Mysuru-scale **synthetic** scenario:

| Entity | Count | Notes |
| --- | --- | --- |
| Authorities | 5 | MCC, MUDA, PWD, CESC, NHAI |
| Departments | 10 | MCC Health & Sanitation, MCC Roads, NHAI Corridor, … |
| Services | 13 | Garbage, Street sweeping, Water supply, NH repair, … |
| Jurisdiction versions | 3 | V1 Delimitation 2020 (superseded), V2 Delimitation 2024 (current), V3 2026 (proposed-only) |
| Jurisdictions | 21 | 9 wards × 2 versions + NH corridor (2) + heritage overlay |
| Wards / Areas / Roads | 9 / 3 / 4 | named localities and road classes (NH/SH/CITY) |
| Routing rules | 25 | temporal + scoped rules, incl. 3 escalation steps (expired pre-2024 rule + 2024 garbage-history rule + heritage pothole escalation) |
| Route extensions | 2 | pothole → PWD State Highways · heritage → MCC Heritage & Public Works |
| Complaints | 9 | incl. a coordinate whose boundary version and route rule flip between V1 and V2 |
| Issue types | 21 | registry incl. 2 legacy + 1 expired codes |
| Conflicts | 1 | GEO_VS_SERVICE: point in MCC geography, rule routes to NHAI |
| Scenario | 1 | V3 proposed rezone, isolated from live jurisdictions |
| Audit log | 2 | seed + version-applied events |

> **IMPORTANT:** All polygons, road lines, and rule assignments are
> **SYNTHETIC DEMO DATA**. They approximate Mysuru's scale so the demo is
> visually believable but are **not** official Mysuru boundaries, and the app
> never fetches external GIS/live APIs. A "SYNTHETIC DEMO DATA - NOT OFFICIAL
> MYSURU BOUNDARIES" note is stamped through the seed.

### Historical replay demo

Complaint `C-1001` sits on a deterministically computed "flip point"
(`app.seed.seed_runner._flip_coords`): its covering ward-mosaic cell differs
between the V1 and V2 boundaries. Under the current seed that coordinate is
**(76.60731308845853, 12.279255877741852)** — it stays in ward **W-01** in both
versions, but the boundary **version** and the routing **rule** flip:
`DELIM-2020 + RULE-GARBAGE-PRE2024` (pre-2024) vs
`DELIM-2024 + RULE-GARBAGE-01`. In the Historical Explorer (`/history`) sliding
the date across the versions shows the transition. The gap between the two
versions bounds — **2023-12-31 → 2024-04-01** (`[2023-12-31, 2024-04-01)`) —
reports `NO_JURISDICTION`, demonstrating that closed-open validity windows
leave no overlapping authority.

The heritage point **(76.635, 12.3125)** is the *responsibility* flip: under
DELIM-2020 it has no matching rule (W-05 unresolved), across the gap no
jurisdiction, and from 2024-04-01 it resolves to the MCC Heritage & Public
Works chain via RULE-HERITAGE-01.

> Note: some older docs/hints quote `(76.6627, 12.2313)` "W-03 → W-01". That
> coordinate is **not** the seeded flip point — in the current seed it is
> outside every version's ward mosaic and reports `NO_JURISDICTION`. The values
> above were verified against live `GET /api/v1/replay/point` output.

---

## GIS / temporal API (P1)

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/gis/jurisdictions` | List/filter jurisdictions (date, kind, version, geometry) |
| `GET` | `/api/v1/gis/jurisdictions/{id}` | Single jurisdiction detail |
| `GET` | `/api/v1/gis/jurisdictions/{id}/versions` | Version history for a code |
| `POST` | `/api/v1/gis/lookup` | Temporal point lookup `{lat, lng, on_date}` |
| `POST` | `/api/v1/gis/validate-geometry` | Validate GeoJSON (+ optional repair with report) |
| `POST` | `/api/v1/gis/repair-geometry` | Repair an invalid geometry, report what changed |
| `POST` | `/api/v1/gis/describe` | Geometry analysis (type, area km², bounds, centroid) |
| `POST` | `/api/v1/gis/operations` | Spatial algebra: intersection/difference/union + predicates |
| `POST` | `/api/v1/gis/transform` | CRS reprojection (defaults EPSG:4326 ↔ EPSG:32643/UTM43N) |
| `GET` | `/api/v1/gis/wards` | Ward lookups (9) |
| `GET` | `/api/v1/gis/areas` | Area lookups (3) |
| `GET` | `/api/v1/gis/roads` | Road corridor lookups (4) |

Lookup statuses: `MATCHED`, `NO_JURISDICTION`, `TEMPORAL_CONFLICT`,
`INVALID_COORDINATES`, `INVALID_GEOMETRY`. Area/length metrics are computed in
UTM zone 43N; exchanges use WGS84 GeoJSON `[lon, lat]`.

---

## API (P0)

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Service metadata |
| `GET` | `/api/v1/health` | App / database / seed / geometry-engine status |
| (docs) | `/docs` | OpenAPI/Swagger UI |

All error responses use a single envelope:

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "…", "details": [] } }
```

Routes are added by phase: P1 GIS, P2 routing, P3 what-if, P4 migration
preview, P5 conflicts (see below).

---

## What-if simulator (P3)

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/whatif/scenarios` | List proposed scenarios (DRAFT) |
| `GET` | `/api/v1/whatif/scenarios/{code}` | Single scenario detail |
| `POST` | `/api/v1/whatif/scenarios` | Create a deterministic DRAFT scenario from GeoJSON geometry |
| `POST` | `/api/v1/whatif/simulate` | Simulate live vs. proposed responsibility (`{longitude, latitude, issue_type_code, on_date}`) |

Scenario creation accepts a GeoJSON `geometry_geojson` and stores the derived
`geometry_wkb` envelope alongside it (shapely path, same as the P1 seed).
Simulation is **strictly read-only**: it resolves the live responsibility
(P2 wiring) and the proposed overlay (`HERITAGE_ZONE_EXPANDED`) without ever
inserting/updating a `jurisdictions`, `jurisdiction_versions`,
`routing_rules`, or `complaints` row. Applying a scenario is an explicit
migration flow in a later phase.

---

## Complaint migration preview (P4)

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/whatif/scenarios/{code}/migration-preview` | Read-only preview of which OPEN complaints would change responsibility under a proposed scenario boundary |

For every OPEN complaint the preview resolves the live responsibility (P2
routing) with a fixed preview date (`2024-06-01`) and, when the complaint's
point lies inside the scenario's stored boundary, the heritage-precinct
responsibility that boundary implies (`RULE-HERITAGE-01` → `HER-01`). A
complaint is a migration candidate when the proposed jurisdiction, department
or service differs from live. The endpoint never inserts, updates or commits
anything — the request session is always rolled back.

---

## Responsibility conflict detector (P5)

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/conflicts` | List detected conflicts (optional `?status=`) |
| `GET` | `/api/v1/conflicts/{conflict_id}` | Single conflict detail |
| `POST` | `/api/v1/conflicts/detect` | Run deterministic detection against live data |

The detector reuses the P2 routing decision table and the P1 temporal
jurisdiction engine to answer, per location + issue + date, *expected*
responsibility (implied by the containing jurisdiction's authority) versus
*routed* responsibility (assigned by the routing rules). Any disagreement — or
gap where no responsibility can be established — is persisted as a
`ResponsibilityConflict` with an OPEN status. Detection is deterministic and
**idempotent**: an identical open conflict (same complaint, issue, date and
type) is never duplicated, so re-running the detector reports `created: 0`.

Conflict types (severity in parentheses):

- `AUTHORITY_MISMATCH` (HIGH) — e.g. C-1003: inside MCC geography, rule routes
  to NHAI; C-1008: inside MCC geography, rule routes to CESC.
- `DEPARTMENT_MISMATCH` (MEDIUM) — the two equally-specific W-05
  construction-waste rules route to MCC-D-RI vs MCC-D-HS.
- `SERVICE_MISMATCH` (MEDIUM) — same tie, SVC-ROAD vs SVC-GARBAGE.
- `TEMPORAL_RULE_CONFLICT` (MEDIUM) — power_outage at C-1008 has no responsible
  actor on 2024-03-15 (a two-version gap between the 2020 and 2024 delimitation
  sets) but routes to CESC on 2024-06-01.
- `RESPONSIBILITY_GAP` (HIGH) — C-1004 has no containing jurisdiction on any
  version; the construction-waste tie can't settle a single actor.

Detecting on the seeded dataset creates 7 conflicts; the seeded `CF-1001`
(`GEO_VS_SERVICE`) remains untouched and the list then holds 8 rows. Only the
`responsibility_conflicts` table is written by `detect` — jurisdictions,
routing rules and complaints stay read-only.

---

## Responsibility graph (P6)

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/graph/resolve?lat=..&lng=..&issue_type=..&date=..` | Explanatory responsibility chain for one point + issue + date |

The graph is a **deterministic projection of the P2 routing decision**, not a
source of truth and not an alternative route engine. Resolving reuses
`ResponsibilityRoutingService.resolve()` and renders the decision as a chain:

`Location → Jurisdiction → Authority → Department → Service → Issue → Escalation`

Nodes carry stable ids (`location:..`, `jurisdiction:..`, `authority:..`,
`department:..`, `service:..`, `issue:..`, `escalation:..`) and edges use only
four types: `RESPONSIBLE_FOR`, `MANAGED_BY`, `HANDLED_BY`, `ESCALATES_TO`.
Every node/edge has a human-readable label so the graph reads without the DB.

Partial chains appear when responsibility cannot be settled:

- `RESPONSIBILITY_UNRESOLVED` — the chain stops at the jurisdiction: the
  construction-waste rules tie at equal priority, so no authority, department
  or service node is emitted and the jurisdiction links straight to the issue
  with a `RESPONSIBLE_FOR` edge.
- `NO_JURISDICTION` — only the `LOCATION` and `ISSUE` nodes remain, linked by a
  `RESPONSIBLE_FOR` edge (e.g. `street_light` at C-1004).

The response also echoes the routing status, the P2 audit id (`routing_id`),
the matched rule id, and a sentence explaining the chain (e.g. *"Location is
inside V.V. Mohalla (W-05) on 2024-06-01 (By DELIM-2024). …"*). Each resolve
still writes a P2 audit row. The frontend shows the graph as a CSS/SVG-free
flow in the "Why this route? · Responsibility Graph" section of Citizen
Routing — no graph database or graph rendering library is involved.

--- 

## Historical jurisdiction replay (P7)

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/replay/point?latitude=..&longitude=..&issue_type=..&start_date=..&end_date=..` | Read-only chronological replay of one coordinate + issue across a date range |

Replay lets one coordinate be asked about **on any date independently**: each
sampled day is a separate P2 routing resolution, so the same point may resolve
to different jurisdictions, versions, or responsibilities on different dates.
The endpoint merges identical consecutive outcomes into **periods** and marks
every **boundary transition** (`boundary_change`), so gaps, version changes,
and responsibility changes are explicit.

- **Reuses the P2 routing service** — period boundaries are simply where the
  P2 decision changes; there is no duplicated routing logic.
- **Strictly read-only** — a replay resolves hundreds of days through P2,
  which would normally write one audit row per resolve, but the request
  session is rolled back, so the audit log is untouched (verified by test).
- **Closed-open `[start, end)`** — `day_count = end − start`; a period spans
  `[effective_from, effective_to)`. An empty window (`start == end`) returns
  `period_count = 0`; `end < start` is a `400 INVALID_DATE_RANGE`.
- **Deterministic** — identical inputs produce byte-identical output.

Response model: `status` (`REPLAY_OK`), echoed `latitude`/`longitude`/
`issue_type`/`start_date`/`end_date`, `day_count`, `period_count`,
`jurisdiction_change_count`, and `periods[]`. Each period carries
`effective_from`/`effective_to`, routing `status`, `boundary_change`,
jurisdiction `code`/`name`/`kind`, boundary `version_code`/`status`,
`ward_code`/`ward_name`, `matched_scope`, the authority / department / service
(`code` + `name` + `id`), the matched `routing_rule_code`/`id`, any
`conflict_rule_codes`, an `explanation`, `reason`, and a compact `chain`
(e.g. `W-05 → A-MCC → MCC-D-HP`, or `(no jurisdiction)`/`(unresolved)` when
responsibility cannot be settled).

Verified examples against the seed:

- **Flip point** `(76.60731308845853, 12.279255877741852)`,
  `garbage_collection`, `2023-06-01 → 2024-06-01`:
  `[2023-06-01, 2023-12-31)` `W-01`/`DELIM-2020`/`RULE-GARBAGE-PRE2024` →
  `[2023-12-31, 2024-04-01)` `NO_JURISDICTION` →
  `[2024-04-01, 2024-06-01)` `W-01`/`DELIM-2024`/`RULE-GARBAGE-01`.
- **Heritage point** `(76.635, 12.3125)`, `heritage_maintenance`,
  `2023-06-01 → 2024-05-01`: `W-05` **unresolved** (no pre-2024 rule) → gap →
  `W-05` **resolved** to `MCC Heritage & Public Works` /
  `RULE-HERITAGE-01` — the same coordinate's responsibility changes across the
  boundary-version change.

---

## Complete frontend integration (P8)

Every completed capability (P0–P7) is exposed through one coherent web
application; all pages call the real backend — no placeholders remain.

| Page | Route | Backend API |
| --- | --- | --- |
| Dashboard | `/` | `GET /health` |
| Citizen Routing | `/route` | `POST /routing/resolve`, `GET /graph/resolve`, `/gis/*`, `/routing/*` |
| Historical Explorer | `/history` | `GET /gis/jurisdictions`, `POST /gis/lookup`, manual version window + `SUPERSEDED` boundary callout |
| Historical Replay | `/replay` | `GET /replay/point` |
| What-If Simulator | `/whatif` | `GET /whatif/scenarios`, `POST /whatif/simulate` |
| Complaint Migration | `/migrations` | `GET /whatif/scenarios/{code}/migration-preview` |
| Responsibility Conflicts | `/conflicts` | `GET /conflicts` |
| Responsibility Graph | `/graph` | `GET /graph/resolve` |

Highlights:

- **Dashboard** — accurate `IMPLEMENTED` module grid (P1–P7), the core formula
  *Responsible Entity = Location + Issue + Date + Jurisdiction Version + Rules*,
  a visual `LOCATION → JURISDICTION → AUTHORITY → DEPARTMENT → SERVICE →
  ESCALATION` pipeline, a backend-health readout, and a **Start Demo** button
  into Citizen Routing.
- **Historical Replay** — a timeline of `ReplayPeriod` cards with summary chips
  (days / periods / jurisdiction changes) and an explicit **BOUNDARY CHANGE**
  marker between periods that lists exactly what changed (jurisdiction, version,
  rule, authority, status).
- **Citizen Routing → replay/explorer** — after routing, "Explore this location
  historically" deep-links the same coordinate + issue into Historical Replay,
  and "Open in Historical Explorer" deep-links it into the map (both pages read
  `?lat&lng` / `?issue` query params).
- **What-If Simulator** — before/after cards (Current boundary → Proposed
  boundary), impact table, potential conflicts and a prominent **SIMULATION
  ONLY · NO LIVE JURISDICTION DATA MODIFIED** ribbon.
- **Complaint Migration** — scenario picker, affected-complaint count and an
  `OLD → NEW` migration table (jurisdiction / authority / department / service
  before and after) under a **READ-ONLY PREVIEW** ribbon.
- **Responsibility Conflicts** — summary counters computed only from the real
  conflict rows (by type, severity and status) plus a compact table.
- **Responsibility Graph** — dedicated page reusing the same graph renderer as
  Citizen Routing.
- **Error handling** — every API-driven page handles loading, backend
  unreachable, invalid coordinates, invalid dates, no jurisdiction, unresolved
  responsibility and empty results without ever exposing a raw stack trace.

The development backend runs on http://127.0.0.1:8011 and the Vite dev proxy
defaults to it; the backend URL is configured with `VITE_API_BASE_URL` /
`VITE_DEV_PROXY_TARGET` (see "Running locally"). The seed's stale
`(76.6627, 12.2313)` "W-03 → W-01" flip-point claim was corrected in the app to
the verified flip coordinate `(76.60731308845853, 12.279255877741852)`
(version/rule flip, ward stays W-01).

---

## Citizen routing: location & mobile (P9)

Citizen Routing now offers three ways to set the routing point before running
"Resolve Responsibility", with a single source of truth for the chosen
location shared by all three inputs:

```ts
selectedLocation = { latitude, longitude, accuracy?, source: "gps" | "map" | "manual" }
```

### 1. Use My Current Location (browser geolocation)

The "Use My Current Location" button fires a **single, one-shot**
`navigator.geolocation.getCurrentPosition` request (`enableHighAccuracy: true`,
10 s timeout) only after an explicit tap — the app never uses
`watchPosition`, never requests the location on page load, and holds no
reading between sessions.

- The detected point recenters the map and is shown with a marker and the
  browser-reported accuracy ring / distance readout (the app never claims
  better accuracy than the browser reports).
- All outcomes are surfaced with friendly guidance: `permission-denied`,
  `unavailable`, `timeout`, `unsupported` and unknown errors each get a message
  plus a retry action where it makes sense.
- **Secure-context requirement:** the Geolocation API is only available in a
  secure context — `https://` for production / LAN, or `http://localhost` /
  `http://127.0.0.1` during development.

### 2. Pick on Map

Toggles a pick mode; tapping the map sets the routing point exactly. The
routing map is now **interactive**: drag to pan, scroll / pinch to zoom, `+/−`
button controls, a reset-view button, and keyboard panning for the map's focus
(`Arrow` keys, `+`/`-`, `Enter` selects the center when picking — the map is
focusable and announces its behavior). A drag vs. tap threshold keeps panning
from accidentally selecting points.

### 3. Enter coordinates manually

An "Enter coordinates manually" details panel accepts a latitude/longitude with
range validation (`lat` ∈ [-90, 90], `lng` ∈ [-180, 180]) and sets the same
routing point. This is the fallback for devices or conditions where the
browser cannot obtain a GPS fix, and for values read from the map or a GPS
device.

### Privacy behavior

- Location is **never persisted** — no `localStorage`, session storage, URL
  params, or backend write beyond the existing `/routing/resolve` request.
- Coordinates are sent **only** to the existing routing API
  (`POST /routing/resolve`) at the moment you resolve responsibility — the
  routing engine and all its constraints are unchanged.
- No tracking, no third-party services, no continuous monitoring, and no
  analytics were added.

### Mobile support

- The sidebar becomes an accessible **drawer** under 900 px (hamburger toggle
  with `aria-expanded`/`aria-controls`, backdrop, scroll lock, closes on
  navigation).
- The routing page stacks mobile-first: Issue/Date → location buttons →
  location readout (`aria-live="polite"` announcements) → Resolve → map →
  result, with full-width, ≥48 px touch targets and horizontally scrollable
  tables.
- A global `:focus-visible` outline keeps keyboard focus visible on every
  control.

---

## Security posture (P0 baseline)

- Config via environment (`TCIVIC_*`) — no hard-coded secrets; `TCIVIC_ADMIN_TOKEN` is empty by default.
- Pydantic validation on all inputs; structured error handlers for validation, HTTP, and app errors.
- `GeometryProvider.validate_geojson_geometry` rejects non-polygon, empty, or self-intersecting GeoJSON (used by uploads from P1).
- CORS allow-list configured by env.
- Append-only audit log seeded and modeled for routing/admin actions.

---

## Known limitations

- Demo data is **synthetic** (deterministic seed): a small Mysuru-like city
  with 9 wards, 3 boundary versions, 23 issue types and 25 routing rules. It is
  designed for evaluation, not real governance.
- The migration page is a **read-only preview**; actually applying a scenario
  to the live boundary set (and the conflict review workflow) is not
  implemented — the P4/P5 pages are honest about this in-app.
- Routing tables are **single-scope decision tables** (per issue, with optional
  scope overrides and escalation) rather than a full graph; conflicts between
  overlapping responsibilities are *detected and reported*, not auto-reconciled.
- The backend pytest suite (currently 168 tests) passes fully with exit 0.
- The demo `SC-V3-REZONE` scenario was seeded with a geometry that, for a
  handful of complaint points near its edge, reports issued by the point-in-
  polygon of *simulate* slightly differently from *migration-preview*; both
  views are internally consistent, and the mismatch never changes routing
  output shown to the user.
- Maps are projected into a fixed local viewBox (SVG); they are resolution-
  independent and resize-safe. Citizen Routing's map supports interactive
  pan/zoom/pinch (plus keyboard panning); the read-only maps on the other pages
  keep the original fit-to-viewBox view.
- Browser geolocation requires a secure context; on plain-HTTP (non-localhost)
  deployments the "Use My Current Location" button degrades to the "not
  supported" guidance and the map / manual entry remain available.

---

## Future PostGIS migration

Nothing above needs to change when moving from the demo store to PostGIS:

1. Add `app/gis/postgis_provider.py` implementing the same `GeometryProvider`
   interface with `ST_Contains`, `ST_Intersects`, `ST_Difference`, GiST
   indexes and `ST_AsGeoJSON`.
2. Flip `TCIVIC_GEOMETRY_ENGINE=postgis` / `TCIVIC_DATABASE_URL=postgresql+psycopg://…`.
3. Port the existing `geometry_wkb` blobs into a PostGIS `geometry(geometry, 4326)`
   column (an Alembic migration).
4. Business logic (routing engine, what-if, migrations) is untouched because
   it calls only the provider abstraction.

---

## Roadmap

- **P0** (done): foundations — DB schema, temporal model, GIS abstraction, seed, shell UI, tests, Docker.
- **P1** (done): GIS + temporal jurisdiction layer — CRS/geometry ops API, point+date lookups with
  overlap detection, Historical Explorer map, tests.
- **P2** (done): civic responsibility routing — issue-type registry, temporal routing-rule
  decision table with escalation, point+issue+date resolution, audit trail, Citizen Routing map.
- **P3** (done): what-if jurisdiction simulator — deterministic DRAFT scenarios with GeoJSON
  geometry, strictly read-only live-vs-proposed simulation against the heritage overlay.
- **P4** (done): complaint migration preview — read-only per-complaint preview of which OPEN
  complaints would change jurisdiction/authority/department/service under a proposed
  scenario boundary.
- **P5** (done): responsibility conflict detector — deterministic, idempotent detection of
  jurisdiction-vs-routing mismatches (authority, department, service, temporal rule
  conflicts and responsibility gaps) persisted with severities and an OPEN/UNDER_REVIEW/
  RESOLVED/DISMISSED status, plus a read API.
- **P6** (done): responsibility graph — deterministic explanatory chain
  Location → Jurisdiction → Authority → Department → Service → Issue → Escalation for any
  point + issue + date, built from the P2 routing decision (no duplicated routing logic)
  and rendered as a simple flow on Citizen Routing.
  (Conflict review workflow, applying migrations, admin boundary management
  remain future.)
- **P7** (done): historical jurisdiction replay — read-only chronological
  replay of one coordinate + issue across a date range via P2, collapsing
  identical outcomes into periods with explicit boundary transitions and
  closed-open `[start, end)` semantics.
- **P8** (done): complete frontend integration — every P0–P7 capability exposed
  through one web app (dashboard with pipeline, replay timeline, what-if
  before/after simulation, read-only migration preview, conflict tables,
  responsibility graph), dev backend default `http://127.0.0.1:8011`, backend
  URL configurable via `VITE_API_BASE_URL` / `VITE_DEV_PROXY_TARGET`.
  (Applying migrations to live isn't implemented — the migration page is a
  read-only preview by design.)
- **P9** (done): citizen routing location + mobile — one-shot browser
  geolocation ("Use My Current Location"), pick-on-map with interactive
  pan/zoom/pinch on the routing map, manual coordinate fallback, a single
  `selectedLocation` source of truth, `aria-live` status readouts, privacy-safe
  (no persistence / no tracking), and a mobile-first layout with an accessible
  sidebar drawer and responsive routing page.