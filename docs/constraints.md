# Hard Constraints We Designed For

[← Back to README](../README.md)

These are the constraints that decide whether a routing solution holds up in
Mysuru. Status key: ✅ handled · ⚠️ partial · ❌ not yet.

| # | Constraint | Status | Video |
|---|---|---|---|
| 1 | Unclear or fragmented jurisdiction ("who is responsible here?") | ✅ | `<mm:ss>` |
| 2 | Responsibility changes over time — boundaries and rules get redrawn/reorganized | ✅ | `<mm:ss>` |
| 3 | Wrong or stale answers destroy trust (no historical accountability) | ✅ | `<mm:ss>` |
| 4 | Overlapping authorities and jurisdiction-vs-rule conflicts | ⚠️ detected + reported, not auto-resolved | `<mm:ss>` |
| 5 | Decisions must be explainable, deterministic and reproducible | ✅ | `<mm:ss>` |

---

## 1. Unclear or fragmented jurisdiction

- **Approach:** every point + date is resolved by point-in-polygon over
  versioned jurisdiction geometry (`GeometryProvider` → `Point.contains`),
  returning `MATCHED` or an explicit `NO_JURISDICTION` / `TEMPORAL_CONFLICT`
  status rather than guessing.
- **What happens in a boundary case:** the containing jurisdiction is named
  with its boundary version, the matched routing rule and an explanation; the
  caller sees exactly why this authority is responsible.
- **Code:** `backend/app/gis/temporal_engine.py`, `backend/app/routing/routing_service.py`

## 2. Date-sensitive responsibility (temporal correctness)

- **Approach:** boundaries and routing rules are versioned data with closed-open
  validity windows `[effective_from, effective_to)`; `jurisdiction_versions`
  group coherent snapshots (`DELIM-2020` superseded, `DELIM-2024` current,
  `DELIM-2026` proposed). A decision is always `f(location, issue, date,
  version, rules)` — the date selects the in-force version, never the latest.
- **Why this matters:** most civic apps assume a static map; here "who was
  responsible last year?" and "what changed between delimitations?" are
  answered by the same replayed decision instead of a stale compromise.
- **Code:** `backend/app/gis/temporal_engine.py`, `backend/app/replay/replay_service.py`

## 3. Wrong or stale answers / historical accountability

- **Approach:** jurisdiction rows are **never mutated or deleted**. Every
  delimitation inserts a new row and records a `jurisdiction_changes`
  transition (`CREATED / MODIFIED / SUPERSEDED`), so historical versions stay
  queryable forever. The historical replay (`GET /replay/point`) replays any
  coordinate + issue across a date range and marks every boundary transition
  explicitly.
- **Code:** `backend/app/gis/temporal_engine.py`, `backend/app/replay/replay_service.py`

## 4. Overlapping authorities and jurisdiction-vs-rule conflicts

- **Approach:** the P5 conflict detector compares *expected* responsibility
  (from the containing jurisdiction) with *routed* responsibility (from the
  routing table) for the same point + issue + date, and persists
  `AUTHORITY_MISMATCH`, `DEPARTMENT_MISMATCH`, `SERVICE_MISMATCH`,
  `TEMPORAL_RULE_CONFLICT` and `RESPONSIBILITY_GAP` findings with severity and
  an OPEN/UNDER_REVIEW/RESOLVED/DISMISSED status. Routing escalations and
  route extensions exist for known multi-authority cases.
- **Limitation:** conflicts are **detected and reported, not auto-reconciled** —
  a human review workflow is future work (see [limitations.md](./limitations.md)).
- **Code:** `backend/app/conflicts/conflict_service.py`

## 5. Explainable, deterministic and reproducible decisions

- **Approach:** routing is a pure decision over seed-visible data: the response
  carries the matched rule code, the governing boundary version, an
  `explanation`, an escalation path, an append-only audit id, and a rendered
  responsibility graph (`Location → Jurisdiction → Authority → Department →
  Service → Issue → Escalation`). Identical inputs produce byte-identical
  output (verified by tests); the seed uses fixed RNG so the demo is fully
  reproducible. No AI/ML is involved anywhere at runtime.
- **Code:** `backend/app/routing/routing_service.py`, `backend/app/graph/graph_service.py`

---

## Hard engineering constraints enforced across the app

| Constraint | How we hold it |
|---|---|
| **Analysis never modifies live data** | What-if simulate, migration preview and replay all resolve through read-only sessions that are rolled back; only `conflicts/detect` writes its own output table. Verified by tests. |
| **No external or paid APIs** | The only network call is OSM base-map tiles (frontend, with an in-app "tiles unavailable (offline?)" fallback). No Google Maps, no API keys, no third-party services, no tracking. |
| **Deterministic seed** | Synthetic Mysuru-scale demo data via fixed RNG; every run produces the same boundaries, rules and complaints. |
| **Input safety** | Pydantic validation on every endpoint; GeoJSON uploads reject non-polygon, empty or self-intersecting geometry; coordinates range-checked; a single structured error envelope. |
| **Append-only audit** | Routing/admin actions write to `audit_logs`; historical jurisdiction rows are immutable. |
| **Secure by default** | Config via `TCIVIC_*` env vars only (no hard-coded secrets); `TCIVIC_ADMIN_TOKEN` empty by default (feature off); CORS allow-list via env. |
| **Offline tolerance** | The full civic dataset and all overlays live locally; only OSM tiles need the network and degrade gracefully. |