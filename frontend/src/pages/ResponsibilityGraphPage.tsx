import { useEffect, useState } from "react";
import { ApiError } from "../api";
import { resolveGraph } from "../api/graph";
import type { GraphResolveResponse } from "../api/graphTypes";
import { fetchIssueTypes } from "../api/routing";
import type { IssueTypeSummary } from "../api/routingTypes";
import { ResponsibilityGraph } from "../components/graph/ResponsibilityGraph";

const DEFAULT_DATE = "2024-06-01";
const DEFAULT_ISSUE = "heritage_maintenance";
const DEFAULT_LAT = "12.3125";
const DEFAULT_LNG = "76.635";

type LoadState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ok"; graph: GraphResolveResponse }
  | { kind: "error"; message: string };

export default function ResponsibilityGraphPage() {
  const [lat, setLat] = useState(DEFAULT_LAT);
  const [lng, setLng] = useState(DEFAULT_LNG);
  const [date, setDate] = useState(DEFAULT_DATE);
  const [issue, setIssue] = useState(DEFAULT_ISSUE);
  const [issueTypes, setIssueTypes] = useState<IssueTypeSummary[]>([]);
  const [state, setState] = useState<LoadState>({ kind: "idle" });

  useEffect(() => {
    let cancelled = false;
    fetchIssueTypes()
      .then((response) => {
        if (!cancelled) setIssueTypes(response.issue_types);
      })
      .catch(() => {
        if (!cancelled) setIssueTypes([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const runGraph = () => {
    const latN = Number(lat);
    const lngN = Number(lng);
    if (!Number.isFinite(latN) || !Number.isFinite(lngN)) {
      setState({ kind: "error", message: "Invalid coordinates: enter numeric latitude and longitude." });
      return;
    }
    if (!issue) {
      setState({ kind: "error", message: "Pick an issue type." });
      return;
    }
    setState({ kind: "loading" });
    resolveGraph({ lat: latN, lng: lngN, issue_type: issue, date })
      .then((graph) => setState({ kind: "ok", graph }))
      .catch((error: unknown) =>
        setState({ kind: "error", message: error instanceof ApiError ? error.message : "Unknown error" }),
      );
  };

  const graph = state.kind === "ok" ? state.graph : null;

  return (
    <section className="page">
      <header className="page-header">
        <h1>Responsibility Graph</h1>
        <p>
          One point + issue + date renders as an explanatory chain —
          Location → Jurisdiction → Authority → Department → Service → Issue →
          Escalation — projected deterministically from the routing decision.
        </p>
      </header>

      <div className="replay-form">
        <div className="gis-toolbar-item">
          <label htmlFor="graph-lat">Latitude</label>
          <input id="graph-lat" type="number" step="0.000001" value={lat} onChange={(e) => setLat(e.target.value)} />
        </div>
        <div className="gis-toolbar-item">
          <label htmlFor="graph-lng">Longitude</label>
          <input id="graph-lng" type="number" step="0.000001" value={lng} onChange={(e) => setLng(e.target.value)} />
        </div>
        <div className="gis-toolbar-item">
          <label htmlFor="graph-issue">Issue</label>
          <select id="graph-issue" value={issue} onChange={(e) => setIssue(e.target.value)}>
            {issueTypes.map((t) => (
              <option key={t.code} value={t.code}>
                {t.name} · {t.code}
              </option>
            ))}
          </select>
        </div>
        <div className="gis-toolbar-item">
          <label htmlFor="graph-date">Date</label>
          <input id="graph-date" type="date" min="2020-01-01" max="2026-12-31" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>
        <button className="btn btn-primary" onClick={runGraph} disabled={state.kind === "loading"}>
          {state.kind === "loading" ? "Resolving…" : "Resolve graph"}
        </button>
      </div>

      {state.kind === "error" && <p className="error-text">{state.message}</p>}
      {state.kind === "loading" && <p className="muted">Building responsibility chain…</p>}
      {state.kind === "idle" && (
        <p className="muted">Enter a point, an issue and a date, then press Resolve graph.</p>
      )}

      {graph && (
        <div className="card resp-graph-card">
          <div className="resp-graph-head">
            <h3>
              {graph.issue_type} · {graph.longitude.toFixed(5)}, {graph.latitude.toFixed(5)} · {graph.date}
            </h3>
            {graph.routing_id !== null && <span className="muted">Routing audit #{graph.routing_id}</span>}
          </div>
          <p className="resp-graph-status">
            Routing status: <code>{graph.status}</code>
          </p>
          <p className="why-route">{graph.explanation}</p>
          <ResponsibilityGraph data={graph} />
        </div>
      )}
    </section>
  );
}