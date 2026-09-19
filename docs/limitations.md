# Known Limitations & Future Scope

[← Back to README](../README.md)

## What Doesn't Work Yet

| Limitation | Why it exists | What we'd do next |
|---|---|---|
| Boundary and rule data are **synthetic, not official** | No official Mysuru GIS layer was available in the hackathon window; the data approximates Mysuru's scale | Integrate MCC GIS / KGIS official ward layers + real routing rules |
| Applying a what-if scenario to live boundaries is **not implemented** | The migration page is a read-only preview by design; the P4/P5 flow stays honest about this | Add an explicit "apply migration" flow with conflict review + approval |
| Conflict review workflow is missing | Out of scope for the 72 h build | Admin screen to triage `UNDER_REVIEW → RESOLVED/DISMISSED` |
| Routing tables are single-scope decision tables, not a full graph | Kept the engine deterministic and explainable (P2) | Extend to a general responsibility graph with auto-reconciled overlaps |
| Production multi-user/auth, rate limiting, deployments beyond Docker | Demo-first scope | Add authN/authZ (officials + admin), paging, observability, CI/CD |

## Edge Cases We Don't Handle

- **Closed-open window edge:** a point exactly on an `effective_to` boundary
  belongs to the *next* interval by design (`[start, end)`); the GUI always
  explains the in-force version.
- **Geometry robustness:** only simple polygon/multipolygon JSON is accepted
  (self-intersections rejected); very thin sliver boundaries are not buffered,
  so a point on a shared ward edge resolves to the geometry that contains it.
- **Browser geolocation accuracy is the browser's to report** — the app never
  claims better precision; GPS is one-shot on demand and never persisted.
- **OSM base tiles need network** — when offline, the tile layer is blank but
  the civic overlays and manual coordinate entry still work.
- **A handful of complaint points near the `SC-V3-REZONE` scenario edge** are
  reported slightly differently by *simulate* vs *migration-preview*; both
  views are internally consistent and this never changes routed output shown
  to the user.

## Scaling to All of Mysuru

| What breaks first | Rough numbers | Fix |
|---|---|---|
| In-Python point-in-polygon scans every jurisdiction row per lookup | 21 jurisdictions today; a full Mysuru run (~400+ wards × versions) slows naive lookups | Switch `TCIVIC_GEOMETRY_ENGINE=postgis` over the same provider interface (GiST indexes) |
| SQLite file store | Single-writer; fine for a demo, not concurrent civic traffic | PostgreSQL/PostGIS (schema is already ORM-portable) |
| Seed-generated synthetic fidelity | 9 wards ≈ 1–2% of Mysuru | Official boundary import + rule governance |
| Decision-table maintenance | 25 rules hand-authored | Rule authoring UI + versioned review workflow |

## Roadmap

1. Official GIS layer integration (MCC / KGIS) + data QA on real boundaries.
2. PostGIS migration behind `GeometryProvider` (no business-logic changes).
3. Applying migrations with a conflict-review/approval workflow.
4. Authentication for officials/admin + complaint status lifecycle end to end.
5. Kannada-language UI and offline-first mobile flows for field staff. |