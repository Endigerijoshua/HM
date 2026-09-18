# Temporal Civic Jurisdiction Digital Twin

HackMysuru 2026 · **Routing** problem statement.

Determines the responsible civic **authority, department and service** for a
location + issue while honoring **jurisdiction boundaries that change over
time**.

```
ResponsibleEntity = f(latitude, longitude, issue_type, date,
                      jurisdiction_version, responsibility_rules)
```

> **P2 status:** P0 (foundations), P1 (GIS/temporal layer) and **P2 (civic
> responsibility routing)** shipped.
>
> - **P0:** repo shell, temporal/versioned database (17 tables), GIS
>   abstraction (SQLite + Shapely), deterministic synthetic demo data, health
>   API, React shell with all module placeholders, tests and Docker config.
> - **P1:** GIS + temporal jurisdiction engine — CRS conversion, geometry
>   validation/repair with reports, describe, spatial algebra, point+date
>   lookups with closed-open window semantics and overlap detection, and a
>   working "Historical Explorer" map page (SVG renderer).
> - **P2:** civic responsibility routing engine + audit trail — issue-type
>   registry (23 codes), a temporal routing-rule decision table (25 rules, 3
>   escalation steps), deterministic point+issue+date resolution
>   (`RESOLVED` / `RESPONSIBILITY_UNRESOLVED` / `NO_JURISDICTION` /
>   `TEMPORAL_CONFLICT` / invalid variants), append-only audit, and a
>   "Citizen Routing" map page.
>
> The what-if / migration / conflict / graph engines arrive in P3.

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
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

On startup the app creates the tables (SQLite) and seeds deterministic demo
data. Open http://localhost:8000/docs for the interactive API.

Health check: `GET /api/v1/health`

### Frontend (dev)

```powershell
cd frontend
npm install
npm run dev
```

Vite proxies `/api/*` to `http://localhost:8000`. If your backend runs on a
different port:

```powershell
$env:VITE_DEV_PROXY_TARGET="http://localhost:8010"; npm run dev
```

### Tests

```powershell
cd backend
.venv\Scripts\python -m pytest          # 158 tests (P0 health/errors + P1 GIS + P2 routing)
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
| Complaints | 9 | incl. a coordinate that **flips ward** between V1 and V2 |
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

Complaint `C-1001` sits on a deterministically computed "flip point": the same
coordinate resolves to **different wards** on 2023-06-01 (V1) vs 2024-06-01
(V2). In the Historical Explorer (`/history`) you can slide the date, click
the flip point (76.6627, 12.2313) on the map, and watch the responsible ward
change from **W-03** (DELIM-2020) to **W-01** (DELIM-2024). The gap between the
two versions (2024-01-01 → 2024-03-31) reports `NO_JURISDICTION`, demonstrating
that closed-open validity windows leave no overlapping authority.

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

Routes under `auth`, `whatif`, `conflicts`, etc. land with P1–P3.

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

## Security posture (P0 baseline)

- Config via environment (`TCIVIC_*`) — no hard-coded secrets; `TCIVIC_ADMIN_TOKEN` is empty by default.
- Pydantic validation on all inputs; structured error handlers for validation, HTTP, and app errors.
- `GeometryProvider.validate_geojson_geometry` rejects non-polygon, empty, or self-intersecting GeoJSON (used by uploads from P1).
- CORS allow-list configured by env.
- Append-only audit log seeded and modeled for routing/admin actions.

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
  (Conflict detector + review workflow, responsibility graph, admin boundary management remain future.)