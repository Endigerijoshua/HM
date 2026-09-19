# AI Usage Disclosure

[← Back to README](./README.md)

> AI tools are **100% permitted** at HackMysuru 1.0. Disclosing them is **mandatory**.
> Reviewers check this file against the commit history and the AI segment of the video.

---

## Summary

| Question | Answer |
|---|---|
| Did we use AI tools during development? | Yes |
| Does our product use AI/ML at runtime? | **No** — every decision is a pure, deterministic function of versioned data |
| Roughly how much of the code was AI-assisted? | `<TODO: confirm exact share, e.g. ~30% of frontend, ~20% of backend — scaffolding, styles, typed API clients, tests; core temporal/GIS and routing logic reviewed line-by-line by the team>` |
| Can every team member explain the AI-assisted code? | `<TODO: confirm — Yes, all AI-generated code was reviewed before merge>` |

---

## 1. AI Tools Used During Development

| Tool | Model / plan | Used by | What we used it for |
|---|---|---|---|
| AI coding assistant (agentic CLI) | `<e.g. Claude-based coding agent>` | `@omkarshirol4-cloud` (and team) | Scaffolding typed frontend API clients (`frontend/src/api/*`), React pages/components, dashboard copy, initial pytest scaffolding, setup/docs authoring |
| GitHub Copilot (optional) | `<e.g. free/auto>` | `<@handle>` | `<autocomplete in components / schemas — add only if actually used>` |

> **TODO before submission:** confirm the actual tools each member used, fill
> the "Used by" and "Model" columns, and adjust the share in the Summary so
> this matches your real workflow. The declaration below must reflect what the
> team can actually explain.

## 2. Where AI Helped in the Codebase

| Area / file | Level of AI help | What a human did |
|---|---|---|
| `frontend/src/api/*` (typed clients + types) | Medium: AI-generated scaffolding | Wrote/validated response contracts against the OpenAPI schema |
| `frontend/src/pages/*`, `components/*` | Medium: AI-assisted React + CSS | Designed the flows, mobile drawer, Leaflet/SVG maps, accessibility |
| `backend/app/gis/*`, `temporal_engine.py` | Low: suggestions only | Designed and reviewed version-window + point-in-polygon logic by hand |
| `backend/app/routing/routing_service.py` | None | Written by hand; the core decision logic was authored and reviewed manually |
| `backend/tests/*` | Medium: AI-assisted parametrization | Chose the fixtures, scenarios and seeded expectations |
| `README.md`, `docs/*`, `ai.md`, `resource.md` | High: drafted by an AI assistant | Team verified facts against the running app and seeded data |

**Commit convention:** commits containing substantial AI-generated code are
tagged `[ai]` in the message.

## 3. AI Inside the Product (runtime)

**None.** The product contains no AI/ML at runtime — no models, no inference,
no LLM calls, no external AI APIs.

- **Accuracy we measured:** n/a — routing is deterministic (`f(location, issue,
  date, version, rules)`), verified by the pytest suite (158 test functions).
- **What happens when the model is wrong:** n/a — no model. Decisions are
  explainable and reproducible by construction; gaps (`NO_JURISDICTION`,
  `RESPONSIBILITY_UNRESOLVED`) are surfaced explicitly instead of guessed.
- **Does it work offline?** Yes — all civic data and overlays are local; only
  optional OSM base tiles need the network.
- **Citizen data sent to third parties:** none. The only external call is OSM
  public map tiles; no tracking or analytics exist.
- **Cost at city scale:** £0 runtime cost for decision logic (pure functions
  over a local DB). PostGIS scaling needs database hosting only.

## 4. Key Prompts (optional, max 5)

| # | Prompt (short) | What we kept | What we changed or rejected |
|---|---|---|---|
| 1 | `"Design a temporal schema where boundaries are never overwritten"` | Closed-open validity windows + `jurisdiction_changes` transitions | Rejected soft-delete / overwrite drafts that would break history queries |
| 2 | `"Draft a typed API client for the FastAPI routing API"` | Structure of `frontend/src/api/routing.ts` | Rewrote against actual OpenAPI shapes returned by the backend |

## 5. How We Verified AI Output

- Every AI-generated function was exercised against the deterministic seed
  data before merging (pytest + `tsc --noEmit` + `vite build` all green).
- AI suggestions that would make analysis write to live jurisdiction tables
  were rejected — what-if, migration-preview and replay are read-only by test.
- Example of a caught bug: an AI-drafted frontend table showed raw timestamps;
  review replaced it with the correct `[start, end)` period rendering used by
  the Replay timeline.

## 6. What We Deliberately Did *Not* Use AI For

- The **jurisdiction routing rules and the temporal decision engine** — the
  core differentiating logic was written and reviewed by the team.
- The **decision log** — written by the team in our own words (linked in
  [resource.md](./resource.md#4-submission-artifacts-google-drive)).

---

**Declaration:** We confirm this disclosure is complete, and every team member
can explain the code listed above.
**Signed:** `<Team Leader name>` on behalf of `<Team Name>` · `<date>`