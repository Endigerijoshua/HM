import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ApiError, fetchReplayPoint } from "../api";
import { fetchIssueTypes } from "../api/routing";
import type { IssueTypeSummary } from "../api/routingTypes";
import type { ReplayPeriod, ReplayPointResponse, ReplayStatus } from "../api/replayTypes";

const DEFAULT_LAT = 12.279255877741852;
const DEFAULT_LNG = 76.60731308845853;
const DEFAULT_ISSUE = "garbage_collection";
const DEFAULT_START = "2023-01-01";
const DEFAULT_END = "2025-01-01";

const QUICK_RUNS = [
  {
    label: "Flip point · garbage 2023→2025",
    lat: 12.279255877741852,
    lng: 76.60731308845853,
    issue: "garbage_collection",
    start: "2023-01-01",
    end: "2025-01-01",
  },
  {
    label: "Heritage · W-05 2023→2024",
    lat: 12.3125,
    lng: 76.635,
    issue: "heritage_maintenance",
    start: "2023-01-01",
    end: "2024-06-01",
  },
  {
    label: "Construction waste · conflict",
    lat: 12.3125,
    lng: 76.6375,
    issue: "construction_waste",
    start: "2024-06-01",
    end: "2024-06-10",
  },
];

const STATUS_TONE: Record<ReplayStatus, string> = {
  RESOLVED: "ok-tag",
  RESPONSIBILITY_UNRESOLVED: "bad-tag",
  NO_JURISDICTION: "muted-tag",
  TEMPORAL_CONFLICT: "warn-tag",
  INVALID_LOCATION: "bad-tag",
  INVALID_ISSUE: "bad-tag",
  INVALID_DATE: "bad-tag",
};

type LoadState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ok"; data: ReplayPointResponse }
  | { kind: "error"; message: string };

function changesBetween(prev: ReplayPeriod, next: ReplayPeriod): string[] {
  const changes: string[] = [];
  const pair = (field: string, a: string | null | undefined, b: string | null | undefined) => {
    if ((a ?? null) !== (b ?? null)) changes.push(`${field}: ${a ?? "(none)"} → ${b ?? "(none)"}`);
  };
  pair("Jurisdiction", prev.jurisdiction_code, next.jurisdiction_code);
  pair("Version", prev.version_code, next.version_code);
  pair("Rule", prev.routing_rule_code, next.routing_rule_code);
  pair("Authority", prev.authority?.code, next.authority?.code);
  if (prev.status !== next.status) changes.push(`Status: ${prev.status} → ${next.status}`);
  return changes;
}

export default function HistoricalReplayPage() {
  const [searchParams] = useSearchParams();

  const latParam = searchParams.get("lat");
  const lngParam = searchParams.get("lng");
  const issueParam = searchParams.get("issue");
  const startParam = searchParams.get("start");
  const endParam = searchParams.get("end");

  const [lat, setLat] = useState(latParam ?? String(DEFAULT_LAT));
  const [lng, setLng] = useState(lngParam ?? String(DEFAULT_LNG));
  const [issue, setIssue] = useState(issueParam ?? DEFAULT_ISSUE);
  const [start, setStart] = useState(startParam ?? DEFAULT_START);
  const [end, setEnd] = useState(endParam ?? DEFAULT_END);
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

  const runReplay = useCallback((latN: number, lngN: number, issueCode: string, startD: string, endD: string) => {
    setState({ kind: "loading" });
    fetchReplayPoint({
      latitude: latN,
      longitude: lngN,
      issue_type: issueCode,
      start_date: startD,
      end_date: endD,
    })
      .then((data) => setState({ kind: "ok", data }))
      .catch((error: unknown) =>
        setState({
          kind: "error",
          message: error instanceof ApiError ? error.message : "Unknown error",
        }),
      );
  }, []);

  const handleRun = () => {
    const latN = Number(lat);
    const lngN = Number(lng);
    if (!Number.isFinite(latN) || !Number.isFinite(lngN)) {
      setState({ kind: "error", message: "Invalid coordinates: enter numeric latitude and longitude." });
      return;
    }
    if (!issue) {
      setState({ kind: "error", message: "Pick an issue type to replay." });
      return;
    }
    if (start >= end) {
      setState({
        kind: "error",
        message: "Invalid date range: start_date must be before end_date (closed-open window).",
      });
      return;
    }
    runReplay(latN, lngN, issue, start, end);
  };

  useEffect(() => {
    if (latParam && lngParam && issueParam) {
      runReplay(Number(latParam), Number(lngParam), issueParam, startParam ?? DEFAULT_START, endParam ?? DEFAULT_END);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const data = state.kind === "ok" ? state.data : null;

  return (
    <section className="page">
      <header className="page-header">
        <h1>Historical Replay</h1>
        <p>
          Replay one location + issue across a date range, day by day. Each day
          is routed independently, identical outcomes are merged into periods,
          and every boundary transition — version change, rule change,
          responsibility gap — is called out explicitly.
        </p>
      </header>

      <div className="gis-toolbar">
        <div className="gis-quick">
          {QUICK_RUNS.map((q) => (
            <button
              key={q.label}
              className="chip"
              onClick={() => {
                setLat(String(q.lat));
                setLng(String(q.lng));
                setIssue(q.issue);
                setStart(q.start);
                setEnd(q.end);
                runReplay(q.lat, q.lng, q.issue, q.start, q.end);
              }}
            >
              {q.label}
            </button>
          ))}
        </div>
      </div>

      <div className="replay-form">
        <div className="gis-toolbar-item">
          <label htmlFor="replay-lat">Latitude</label>
          <input id="replay-lat" type="number" step="0.000001" value={lat} onChange={(e) => setLat(e.target.value)} />
        </div>
        <div className="gis-toolbar-item">
          <label htmlFor="replay-lng">Longitude</label>
          <input id="replay-lng" type="number" step="0.000001" value={lng} onChange={(e) => setLng(e.target.value)} />
        </div>
        <div className="gis-toolbar-item">
          <label htmlFor="replay-issue">Issue</label>
          <select id="replay-issue" value={issue} onChange={(e) => setIssue(e.target.value)}>
            {issueTypes.map((t) => (
              <option key={t.code} value={t.code}>
                {t.name} · {t.code}
              </option>
            ))}
          </select>
        </div>
        <div className="gis-toolbar-item">
          <label htmlFor="replay-start">From (inclusive)</label>
          <input id="replay-start" type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        </div>
        <div className="gis-toolbar-item">
          <label htmlFor="replay-end">To (exclusive)</label>
          <input id="replay-end" type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
        </div>
        <button className="btn btn-primary" onClick={handleRun} disabled={state.kind === "loading"}>
          {state.kind === "loading" ? "Replaying…" : "Replay"}
        </button>
      </div>

      {state.kind === "error" && <p className="error-text">{state.message}</p>}
      {state.kind === "loading" && <p className="muted">Replaying day-by-day…</p>}
      {state.kind === "idle" && (
        <p className="muted">Pick a quick run above or enter a point, issue and range, then press Replay.</p>
      )}

      {data && (
        <div className="replay-results">
          <div className="replay-summary">
            <span className="summary-chip">Range {data.start_date} → {data.end_date} <em>(closed-open)</em></span>
            <span className="summary-chip">{data.day_count} days</span>
            <span className="summary-chip">{data.period_count} period{data.period_count === 1 ? "" : "s"}</span>
            <span className="summary-chip">
              {data.jurisdiction_change_count} jurisdiction change
              {data.jurisdiction_change_count === 1 ? "" : "s"}
            </span>
            <span className="summary-chip">
              {data.longitude.toFixed(5)}, {data.latitude.toFixed(5)} · {data.issue_type}
            </span>
          </div>

          {data.period_count === 0 && (
            <div className="card">
              <p className="muted">No days in the requested window (start equals end).</p>
            </div>
          )}

          <div className="replay-timeline">
            {data.periods.map((period, index) => {
              const prev = data.periods[index - 1];
              const changes = prev ? changesBetween(prev, period) : [];
              return (
                <div key={`${period.effective_from}-${period.effective_to}`} className="replay-period">
                  {index > 0 && (
                    <div className="boundary-marker">
                      <span className="boundary-line" aria-hidden="true" />
                      <span className="boundary-badge">BOUNDARY CHANGE ↓</span>
                      {changes.length > 0 && (
                        <span className="boundary-changes">{changes.join(" · ")}</span>
                      )}
                      <span className="boundary-date">
                        at {prev?.effective_to}
                      </span>
                    </div>
                  )}
                  <div className={`card replay-period-card${period.boundary_change ? " transition" : ""}`}>
                    <div className="module-head">
                      <span className="replay-period-range">
                        {period.effective_from} → {period.effective_to}
                      </span>
                      <span className={`result-status ${STATUS_TONE[period.status]}`}>{period.status}</span>
                    </div>

                    {period.chain && <p className="replay-chain">{period.chain}</p>}

                    <div className="kv replay-kv">
                      <div>
                        <dt>Jurisdiction</dt>
                        <dd>{period.jurisdiction_code ?? "(none)"}{period.jurisdiction_name ? ` · ${period.jurisdiction_name}` : ""}</dd>
                      </div>
                      <div>
                        <dt>Version</dt>
                        <dd>{period.version_code ?? "(none)"}{period.version_status ? ` · ${period.version_status}` : ""}</dd>
                      </div>
                      <div>
                        <dt>Ward</dt>
                        <dd>{period.ward_code ? `${period.ward_code} · ${period.ward_name ?? ""}` : "(none)"}</dd>
                      </div>
                      <div>
                        <dt>Authority</dt>
                        <dd>{period.authority ? `${period.authority.code} · ${period.authority.name}` : "(none)"}</dd>
                      </div>
                      <div>
                        <dt>Department</dt>
                        <dd>{period.department ? `${period.department.code} · ${period.department.name}` : "(none)"}</dd>
                      </div>
                      <div>
                        <dt>Service</dt>
                        <dd>{period.service ? `${period.service.code} · ${period.service.name}` : "(none)"}</dd>
                      </div>
                      <div>
                        <dt>Rule</dt>
                        <dd>{period.routing_rule_code ? <code>{period.routing_rule_code}</code> : "(none)"}</dd>
                      </div>
                      {period.matched_scope && (
                        <div>
                          <dt>Scope</dt>
                          <dd>{period.matched_scope}</dd>
                        </div>
                      )}
                      {period.conflict_rule_codes.length > 0 && (
                        <div>
                          <dt>Conflicting rules</dt>
                          <dd>{period.conflict_rule_codes.map((c) => <code key={c}>{c}</code>).join(" ")}</dd>
                        </div>
                      )}
                    </div>

                    {period.explanation && <p className="why-route">{period.explanation}</p>}
                    {period.reason && <p className="muted">{period.reason}</p>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}