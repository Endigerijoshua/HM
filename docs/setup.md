# Setup & Run Instructions

[← Back to README](../README.md)

A reviewer (or judge) should have the app running in under ~5 minutes using
either the Docker stack or the local dev commands below. No secrets or external
services are required — the backend seeds its own demo data on first start.

## Prerequisites

| Tool | Version |
|---|---|
| Python | 3.13 (tested; 3.11+ works) |
| Node.js + npm | 20.x+ (Vite 5) |
| Docker + Compose (optional) | Compose v2 |

## 1. Clone

```bash
git clone https://github.com/omkarshirol4-cloud/HM.git
cd HM
```

## 2. Environment Variables (all optional)

Backend defaults work out of the box; the frontend proxies the dev backend.
Copy the example files only if you want to override:

```bash
# backend/.env — TCIVIC_* settings (see backend/app/config.py)
```

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `TCIVIC_DATABASE_URL` | No | `sqlite:///./temporal_civic.db` | SQLAlchemy DB URL (PostGIS-friendly later) |
| `TCIVIC_SEED_ON_STARTUP` | No | `true` | Load deterministic demo data at startup |
| `TCIVIC_CORS_ORIGINS` | No | `http://localhost:5173,http://localhost:8080` | Allowed browser origins |
| `TCIVIC_LOG_LEVEL` | No | `INFO` | Logging verbosity |
| `TCIVIC_GEOMETRY_ENGINE` | No | `shapely` | `shapely` (demo) / `postgis` (future) |
| `TCIVIC_ADMIN_TOKEN` | No | *(empty = off)* | Demo-only admin token |
| `VITE_API_BASE_URL` | No | `/api/v1` | API base path for the frontend |
| `VITE_DEV_PROXY_TARGET` | No | `http://127.0.0.1:8011` | Vite dev-proxy target |

> Never commit real secrets. Only `.env.example` files are committed.

## 3. Install & Seed Demo Data

Seeding is automatic (`TCIVIC_SEED_ON_STARTUP=true`): on startup the app
creates the SQLite tables and loads the deterministic demo dataset —
5 authorities, 10 departments, 13 services, 3 jurisdiction versions
(`DELIM-2020` superseded, `DELIM-2024` current, `DELIM-2026` proposed-only),
21 jurisdictions (9 wards × 2 versions + NH corridor + heritage overlay),
25 routing rules, 9 complaints, 21 issue types and 1 conflict. No manual
migration or seed step is needed in local dev.

## 4. Run — Option A: local dev (recommended for judges)

Backend (port **8011**):

```bash
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8011
```

Frontend dev server (port **5173**, proxies `/api` → 8011 so the browser never
hits CORS):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. API docs (Swagger UI) at http://127.0.0.1:8011/docs.

## 4b. Run — Option B: Docker stack

```bash
docker compose up --build
```

- Backend → http://localhost:8000
- Frontend (nginx, reverse-proxies `/api`) → http://localhost:8080

The compose file mounts a named volume (`civic-data`) so the SQLite database
survives restarts.

## Recommended demo path (3–5 min)

Detailed script in [DEMO.md](../DEMO.md). The shortest route:

1. Dashboard → **Start Demo** → Citizen Routing.
2. Tap the quick flip **"Garbage collection · V1/V2 flip"** (resolves on
   2024-06-01 to W-01 · DELIM-2024 · RULE-GARBAGE-01 with the full chain).
3. **"Explore this location historically →"** — watch 3 periods / 2 boundary
   changes across `DELIM-2020` → gap → `DELIM-2024`.
4. **What-If Simulator** → "Heritage expansion · inside rezone" → Simulate
   (read-only before/after).
5. **Complaint Migration** → 3 of the open complaints require migration.
6. **Responsibility Graph** → the default heritage point renders the full
   `Location → Jurisdiction → Authority → Department → Service → Issue →
   Escalation` chain.

## Tests

```bash
cd backend
.venv\Scripts\python -m pytest -q     # backend (158 test functions, exit 0)

cd frontend
npm run typecheck                      # tsc --noEmit
npm run build                          # tsc --noEmit + vite build
```

## Demo / seed data reference (deterministic, synthetic)

| Entity | Count | Notes |
| --- | --- | --- |
| Authorities | 5 | MCC, MUDA, PWD, CESC, NHAI |
| Departments | 10 | MCC Health & Sanitation, MCC Roads, NHAI Corridor, … |
| Services | 13 | Garbage, Street sweeping, Water supply, NH repair, … |
| Jurisdiction versions | 3 | V1 Delimitation 2020 (superseded), V2 Delimitation 2024 (current), V3 2026 (proposed-only) |
| Jurisdictions | 21 | 9 wards × 2 versions + NH corridor (2) + heritage overlay |
| Wards / Areas / Roads | 9 / 3 / 4 | named localities and road classes (NH/SH/CITY) |
| Routing rules | 25 | temporal + scoped rules, incl. 3 escalation steps |
| Route extensions | 2 | pothole → PWD State Highways · heritage → MCC Heritage & Public Works |
| Complaints | 9 | incl. a coordinate whose boundary version and route rule flip between V1 and V2 |
| Issue types | 21 | registry incl. 2 legacy + 1 expired codes |
| Conflicts | 1 | GEO_VS_SERVICE: point in MCC geography, rule routes to NHAI |
| Scenario | 1 | SC-V3-REZONE (V3 proposed rezone, isolated from live jurisdictions) |
| Audit log | 2 | seed + version-applied events |

All polygons, road lines and rule assignments are **SYNTHETIC DEMO DATA —
NOT OFFICIAL MYSURU BOUNDARIES**.

### Verified demo anchors (replay output, verified against live API)

- **Flip point** `(76.60731308845853, 12.279255877741852)` + `garbage_collection`,
  `2023-06-01 → 2024-06-01`:
  `[2023-06-01, 2023-12-31)` W-01 / DELIM-2020 / RULE-GARBAGE-PRE2024 →
  `[2023-12-31, 2024-04-01)` NO_JURISDICTION → `[2024-04-01, 2024-06-01)`
  W-01 / DELIM-2024 / RULE-GARBAGE-01.
- **Heritage point** `(76.635, 12.3125)` + `heritage_maintenance`,
  `2023-06-01 → 2024-05-01`: W-05 **unresolved** (no pre-2024 rule) → gap →
  W-05 **resolved** to MCC Heritage & Public Works / RULE-HERITAGE-01.
- The stale `(76.6627, 12.2313)` "W-03 → W-01" coordinate quoted in older docs is
  **not** a seeded flip point — it reports NO_JURISDICTION in the current seed.

## Troubleshooting

| Problem | Fix |
|---|---|
| Port 8011 in use (stale data in demo) | `Get-NetTCPConnection -LocalPort 8011` → kill the old process, restart uvicorn (fresh seed). |
| "Backend is unreachable" in the UI | Restart uvicorn on 8011; Dashboard card + sidebar dot go red otherwise. |
| Frontend can't reach backend on a different port | `$env:VITE_DEV_PROXY_TARGET="http://localhost:8010"; npm run dev` |
| Geolocation button reports "not supported" | Geolocation needs a secure context (`https://` or `http://localhost`). The map + manual coordinates remain available. |
| OSM tiles don't load (offline) | Locally-drawn jurisdiction overlays still render; an in-app "tiles unavailable (offline?)" notice appears. |