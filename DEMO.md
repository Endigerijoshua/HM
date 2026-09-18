# Judge Demo Script — Temporal Civic Jurisdiction Digital Twin

**Duration: 3–5 minutes.** One browser window, one story.
Play the **flip point** `(76.607313, 12.279256)` — a single coordinate whose
responsibility **changes with the date** — through the whole journey.

---

## Setup (before the judges arrive)

```powershell
# Terminal 1 — backend (fresh DB, deterministic seed, port 8011)
cd backend
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8011

# Terminal 2 — frontend dev server (proxies /api to 127.0.0.1:8011)
cd frontend
npm run dev
```

Open `http://localhost:5173`. Check the green **backend** dot in the sidebar
and the "Backend connection" card on the Dashboard before starting. (If the
demo shows stale data, kill any old process on 8011 and restart the backend —
`Get-NetTCPConnection -LocalPort 8011` to check.)

---

## The script (step by step)

### 1. A citizen submits a civic issue — Dashboard → Citizen Routing *(30 s)*

- Land on the **Dashboard**. Read the formula out loud:
  *"Responsible Entity = Location + Issue + Date + Jurisdiction Version + Rules."*
- Point at the pipeline: Location → Jurisdiction → Authority → Department →
  Service → Escalation.
- Press **Start Demo → Citizen Routing**.

### 2. The system determines the responsible authority *(60 s)*

- Tap the quick flip **"Garbage collection · V1/V2 flip"**.
- The result card resolves on **2024-06-01**:
  - Jurisdiction: **W-01 · Chamaraja** (version **DELIM-2024**)
  - Authority: **A-MCC · Mysuru City Corporation**
  - Department: **MCC-D-HS · Health & Sanitation**
  - Service: **SVC-GARBAGE · Garbage collection**
  - Rule: **RULE-GARBAGE-01**, with a "why this route?" explanation and
    escalation path.
- Note the marker on the map and the **Routing status: RESOLVED** audit id.

### 3–4. The same location across different dates — Historical Replay *(60 s)*

- Click **"Explore this location historically →"** (deep-links the same
  coordinate into Replay, 2023-01-01 → 2025-01-01).
- The timeline shows **3 periods, 2 boundary changes**:
  - `[2023-06-01, 2023-12-31)` → **W-01 · DELIM-2020 · RULE-GARBAGE-PRE2024**
  - **[BOUNDARY CHANGE ↓]** at 2023-12-31 → `(no jurisdiction)` gap
  - `[2024-04-01, 2025-01-01)` → **W-01 · DELIM-2024 · RULE-GARBAGE-01**
- This is the killer point: **the ward code stays W-01, but the responsibility
  (version + rule) changed overnight.** Try **"Heritage · W-05"** for a second
  example where responsibility goes from *unresolved* to *resolved*.

### 5. Simulating a proposed boundary — What-If Simulator *(45 s)*

- Go to **What-If Simulator**. Read the ribbon:
  *"SIMULATION ONLY · NO LIVE JURISDICTION DATA MODIFIED."*
- Tap **"Heritage expansion · inside rezone"** → hit **Simulate**.
- Show the **before/after** cards (Current live boundary vs Proposed scenario
  boundary), the impact metric (**Heritage precinct area 2 → 5 km²**) and the
  flagged **potential conflict: HERITAGE**.

### 6. Affected complaints → migrations identified *(30 s)*

- Open **Complaint Migration Preview** (scenario auto-loads `SC-V3-REZONE`).
- Banner: **READ-ONLY PREVIEW · NO MIGRATION APPLIED**.
- **3 of 7 open complaints** must migrate → show the `OLD → NEW` table for one
  row (e.g. **C-1002 water_supply: W-05 → HER-01**), badge **MIGRATION
  REQUIRED**.

### 7. Responsibility conflicts *(20 s)*

- Open **Responsibility Conflicts**. Real data from `GET /conflicts`:
  1 conflict, **GEO_VS_SERVICE · HIGH · OPEN**, with expected vs routed
  authority/department/service and the explanation. No invented numbers.

### 8. Responsibility graph — why this route *(20 s)*

- Open **Responsibility Graph**. Default shows **heritage_maintenance ·
  76.6350, 12.3125 · 2024-06-01**:
  `Location → JURISDICTION (W-05) → AUTHORITY (A-MCC) → DEPARTMENT
  (MCC-D-HP) → SERVICE (SVC-HERITAGE) → ISSUE → ESCALATION`, plus the
  explanation. The same chain is embedded on Citizen Routing.

### Closing ~15 s

> *"One deterministic pipeline: a coordinate + issue + date is enough to know
> who is responsible, what changed historically, what a boundary change would
> do, which complaints it would touch, and where geography and rules disagree —
> all read-only, all reproducible, all on timestamped jurisdiction versions."*

---

## Failover cheat-sheet

- **Backend not reachable?** Pages show a graceful "Backend is unreachable"
  message (Dashboard card + sidebar dot go red). Restart uvicorn on 8011 and
  reload.
- **Don't have the exact flip coords on hand?** All quick flips / chips are
  pre-validated demo points — any of them resolves.
- **Conflict page empty?** It means the re-detection ran and found nothing —
  show "No responsibility conflicts detected" (a valid outcome).
- **Time is short?** Skip What-If detail; go straight Dashboard → Route →
  Replay → Migration → Graph.