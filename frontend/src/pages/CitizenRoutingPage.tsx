import { useCallback, useEffect, useState } from "react";
import { ApiError, fetchAreas, fetchJurisdictions, fetchRoads } from "../api";
import { fetchIssueTypes, fetchRoutingRules, resolveRoute } from "../api/routing";
import type { AreaSummary, JurisdictionSummary, RoadSummary } from "../api/gisTypes";
import type {
  IssueTypeSummary,
  RoutingResult,
  RoutingRuleSummary,
  RoutingStatus,
} from "../api/routingTypes";
import { JurisdictionMap } from "../components/map/JurisdictionMap";

const MIN_DATE = "2020-01-01";
const MAX_DATE = "2026-12-31";
const DEFAULT_DATE = "2024-06-01";

const QUICK_DATES = [
  { label: "V1 · DELIM-2020", date: "2023-06-01" },
  { label: "Gap · no jurisdiction", date: "2024-01-05" },
  { label: "V2 · DELIM-2024", date: "2024-06-01" },
];

/** Deterministic demo points (representative points of V2 geometries). */
const SCENARIOS = [
  {
    label: "Pothole · W-05",
    issue: "pothole",
    point: { lat: 12.276616211968356, lng: 76.6847217167165 },
  },
  {
    label: "Construction waste · W-05 conflict",
    issue: "construction_waste",
    point: { lat: 12.276616211968356, lng: 76.6847217167165 },
  },
  {
    label: "Heritage maintenance · HER-01",
    issue: "heritage_maintenance",
    point: { lat: 12.3125, lng: 76.635 },
  },
  {
    label: "Garbage · flip point",
    issue: "garbage",
    point: { lat: 12.2313, lng: 76.6627 },
  },
];

type LoadState =
  | { kind: "loading" }
  | { kind: "ok" }
  | { kind: "error"; message: string };

const STATUS_TONE: Record<RoutingStatus, string> = {
  RESOLVED: "ok-tag",
  RESPONSIBILITY_UNRESOLVED: "bad-tag",
  NO_JURISDICTION: "muted-tag",
  TEMPORAL_CONFLICT: "warn-tag",
  INVALID_LOCATION: "bad-tag",
  INVALID_ISSUE: "bad-tag",
  INVALID_DATE: "bad-tag",
};

export default function CitizenRoutingPage() {
  const [onDate, setOnDate] = useState(DEFAULT_DATE);
  const [issueType, setIssueType] = useState("");
  const [issueTypes, setIssueTypes] = useState<IssueTypeSummary[]>([]);
  const [jurisdictions, setJurisdictions] = useState<JurisdictionSummary[]>([]);
  const [areas, setAreas] = useState<AreaSummary[]>([]);
  const [roads, setRoads] = useState<RoadSummary[]>([]);
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [activeVersions, setActiveVersions] = useState<string[]>([]);
  const [rules, setRules] = useState<RoutingRuleSummary[]>([]);

  const [probe, setProbe] = useState<{ lat: number; lng: number } | null>(null);
  const [result, setResult] = useState<RoutingResult | null>(null);
  const [resultError, setResultError] = useState<string | null>(null);
  const [resolving, setResolving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setState({ kind: "loading" });
    Promise.all([fetchAreas(), fetchRoads()])
      .then(([areasRes, roadsRes]) => {
        if (cancelled) return;
        setAreas(areasRes.areas);
        setRoads(roadsRes.roads);
        setState({ kind: "ok" });
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({
            kind: "error",
            message: error instanceof ApiError ? error.message : "Unknown error",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchIssueTypes()
      .then((response) => {
        if (cancelled) return;
        setIssueTypes(response.issue_types);
        setIssueType((current) => {
          if (current) return current;
          const fallback =
            response.issue_types.find((t) => t.code === "pothole") ??
            response.issue_types.find((t) => t.is_active) ??
            response.issue_types[0];
          return fallback?.code ?? "";
        });
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({
            kind: "error",
            message: error instanceof ApiError ? error.message : "Unknown error",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setState({ kind: "loading" });
    fetchJurisdictions({ date: onDate, includeGeometry: true })
      .then((response) => {
        if (cancelled) return;
        setJurisdictions(response.jurisdictions);
        setActiveVersions(
          Array.from(
            new Set(response.jurisdictions.map((j) => j.version_code).filter(Boolean)),
          ) as string[],
        );
        setState({ kind: "ok" });
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({
            kind: "error",
            message: error instanceof ApiError ? error.message : "Unknown error",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [onDate]);

  useEffect(() => {
    let cancelled = false;
    if (!issueType) return;
    fetchRoutingRules({ issueType, activeOn: onDate })
      .then((response) => {
        if (!cancelled) setRules(response.rules);
      })
      .catch(() => {
        if (!cancelled) setRules([]);
      });
    return () => {
      cancelled = true;
    };
  }, [issueType, onDate]);

  const runResolve = useCallback(
    (lat: number, lng: number, issue: string, date: string) => {
      setProbe({ lat, lng });
      setResolving(true);
      setResultError(null);
      setResult(null);
      resolveRoute({ lat, lng, issue_type: issue, date })
        .then((res) => {
          setProbe({ lat: res.latitude, lng: res.longitude });
          setResult(res);
        })
        .catch((error: unknown) =>
          setResultError(error instanceof ApiError ? error.message : "Unknown error"),
        )
        .finally(() => setResolving(false));
    },
    [],
  );

  const handleSelect = (lat: number, lng: number) => {
    if (!issueType) return;
    runResolve(lat, lng, issueType, onDate);
  };

  const handleScenario = (issue: string, point: { lat: number; lng: number }) => {
    setIssueType(issue);
    runResolve(point.lat, point.lng, issue, onDate);
  };

  const categories = Array.from(new Set(issueTypes.map((t) => t.category))).sort();
  const highlightCode = result?.jurisdiction_code ?? null;

  return (
    <section className="page">
      <header className="page-header">
        <h1>Citizen Routing</h1>
        <p>
          Pick a location, an issue and a date to attribute civic responsibility:
          the engine returns the authority, department and service that must act —
          with a step-by-step escalation path and a "why this route?" explanation.
        </p>
      </header>

      <div className="gis-toolbar">
        <div className="gis-toolbar-item">
          <label htmlFor="issue-type">Issue</label>
          <select
            id="issue-type"
            value={issueType}
            onChange={(event) => setIssueType(event.target.value)}
          >
            <option value="">Select an issue…</option>
            {categories.map((category) => (
              <optgroup key={category} label={category}>
                {issueTypes
                  .filter((t) => t.category === category)
                  .map((t) => (
                    <option key={t.code} value={t.code}>
                      {t.name} · {t.code}
                    </option>
                  ))}
              </optgroup>
            ))}
          </select>
        </div>
        <div className="gis-toolbar-item">
          <label htmlFor="on-date">Effective date</label>
          <input
            id="on-date"
            type="date"
            min={MIN_DATE}
            max={MAX_DATE}
            value={onDate}
            onChange={(event) => setOnDate(event.target.value)}
          />
        </div>
        <div className="gis-quick">
          {QUICK_DATES.map((q) => (
            <button key={q.date} className="chip" onClick={() => setOnDate(q.date)}>
              {q.label}
            </button>
          ))}
        </div>
        <div className="gis-quick">
          {SCENARIOS.map((s) => (
            <button
              key={s.label}
              className="chip"
              onClick={() => handleScenario(s.issue, s.point)}
            >
              {s.label}
            </button>
          ))}
        </div>
        {state.kind === "ok" && (
          <span className="gis-count">{jurisdictions.length} jurisdictions in force</span>
        )}
      </div>

      {state.kind === "error" && <p className="error-text">{state.message}</p>}
      {state.kind === "loading" && <p className="muted">Loading jurisdictions…</p>}

      <div className="gis-layout">
        <div className="card gis-map-card">
          <JurisdictionMap
            jurisdictions={jurisdictions}
            areas={areas}
            roads={roads}
            probe={probe}
            highlightCode={highlightCode}
            activeVersionLabels={activeVersions}
            onSelect={handleSelect}
          />
          <p className="muted gis-click-hint">
            {issueType
              ? `Click anywhere on the map to route "${issueType}" on ${onDate}.`
              : "Pick an issue type first, then click the map."}
          </p>
        </div>

        <div className="card gis-result-card">
          <h3>Routing result</h3>
          {resolving && <p className="muted">Resolving responsibility…</p>}
          {resultError && <p className="error-text">{resultError}</p>}
          {!resolving && !resultError && !result && (
            <p className="muted">
              Choose a scenario chip or click a location on the map to route an issue.
            </p>
          )}
          {!resolving && !resultError && result && <RoutingResultView result={result} />}
        </div>
      </div>

      {rules.length > 0 && (
        <div className="card rules-card">
          <h3>Decision table · {rules.length} rule{rules.length === 1 ? "" : "s"} in force for{" "}
            <code>{issueType}</code> on <code>{onDate}</code></h3>
          <table className="rules-table">
            <thead>
              <tr>
                <th>Rule</th>
                <th>Scope</th>
                <th>Prio</th>
                <th>In force</th>
                <th>Authority → Service</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr key={rule.id}>
                  <td>
                    <code>{rule.code}</code>
                  </td>
                  <td>{rule.scope}</td>
                  <td>{rule.priority}</td>
                  <td>
                    {rule.effective_from}
                    {rule.effective_to ? ` → ${rule.effective_to}` : " → open"}
                  </td>
                  <td>
                    {rule.authority_code} → {rule.service_code}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="muted gis-demohint">
        Tip: the construction-waste scenario on W-05 (V2) deliberately triggers two equal-priority
        jurisdiction rules → <code>RESPONSIBILITY_UNRESOLVED</code>. Try the same issue on any other
        V2 ward to see it resolve. Replay garbage on the flip point across V1/V2 to watch the rule
        change from <code>RULE-GARBAGE-HIST</code> (MCC-D-HS) to <code>RULE-GARBAGE</code>.
      </p>
    </section>
  );
}

function RoutingResultView({ result }: { result: RoutingResult }) {
  return (
    <div className="gis-result">
      <div className="module-head">
        <span className={`result-status ${STATUS_TONE[result.status]}`}>{result.status}</span>
      </div>

      <dl className="kv">
        <div>
          <dt>Point</dt>
          <dd>
            {result.longitude.toFixed(5)}, {result.latitude.toFixed(5)}
          </dd>
        </div>
        <div>
          <dt>Issue</dt>
          <dd>{result.issue_type}</dd>
        </div>
        <div>
          <dt>Date</dt>
          <dd>{result.effective_date}</dd>
        </div>
        {result.jurisdiction_code && (
          <div>
            <dt>Jurisdiction</dt>
            <dd>
              {result.jurisdiction_code} · {result.jurisdiction_kind ?? "?"}
            </dd>
          </div>
        )}
        {result.ward_code && (
          <div>
            <dt>Ward</dt>
            <dd>
              {result.ward_code} · {result.ward_name ?? ""}
            </dd>
          </div>
        )}
        {result.version_code && (
          <div>
            <dt>Version</dt>
            <dd>{result.version_code}</dd>
          </div>
        )}
      </dl>

      {result.status === "RESOLVED" && result.authority && result.department && result.service && (
        <>
          <div className="actor-chain">
            <DirectorActor label="Authority" actor={result.authority} />
            <span className="actor-arrow">→</span>
            <DirectorActor label="Department" actor={result.department} />
            <span className="actor-arrow">→</span>
            <DirectorActor label="Service" actor={result.service} />
          </div>
          <dl className="kv">
            {result.matched_scope && (
              <div>
                <dt>Matched scope</dt>
                <dd>{result.matched_scope}</dd>
              </div>
            )}
            {result.sla_days !== null && (
              <div>
                <dt>SLA</dt>
                <dd>{result.sla_days} days</dd>
              </div>
            )}
            {result.routing_rule_code && (
              <div>
                <dt>Rule</dt>
                <dd>
                  <code>{result.routing_rule_code}</code>
                </dd>
              </div>
            )}
          </dl>
          {result.escalation_path.length > 0 && (
            <div className="escalation">
              <h4>Escalation path</h4>
              {result.escalation_path.map((step) => (
                <div key={step.step_number} className="escalation-step">
                  <span className="escalation-step-no">#{step.step_number}</span>
                  {step.authority.name}
                  {step.note ? <span className="muted"> — {step.note}</span> : null}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {result.status === "RESPONSIBILITY_UNRESOLVED" && result.conflict_rule_codes.length > 0 && (
        <div className="conflict-box">
          <h4>Responsibility conflict</h4>
          <p>
            Two equal-priority rules both matched and disagree on ownership:
          </p>
          <ul className="conflict-list">
            {result.conflict_rule_codes.map((code) => (
              <li key={code}>
                <code>{code}</code>
              </li>
            ))}
          </ul>
          <p className="muted">An authority must break the tie before the issue can be routed.</p>
        </div>
      )}

      {result.explanation && <p className="why-route">{result.explanation}</p>}
      {result.reason && <p className="muted">{result.reason}</p>}
      {result.audit_id !== null && (
        <p className="muted">Audit: routing.resolve #{result.audit_id}</p>
      )}
    </div>
  );
}

function DirectorActor({ label, actor }: { label: string; actor: { code: string; name: string } }) {
  return (
    <div className="actor">
      <span className="actor-label">{label}</span>
      <span className="actor-name">{actor.name}</span>
      <code className="actor-code">{actor.code}</code>
    </div>
  );
}