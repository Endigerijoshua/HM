import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ApiError, fetchAreas, fetchJurisdictions, fetchReplayPoint, fetchRoads } from "../api";
import { fetchIssueTypes } from "../api/routing";
import type { IssueTypeSummary } from "../api/routingTypes";
import type {
  AreaSummary,
  JurisdictionSummary,
  RoadSummary,
} from "../api/gisTypes";
import type { ReplayPeriod, ReplayPointResponse, ReplayStatus } from "../api/replayTypes";
import { JurisdictionMap } from "../components/map/JurisdictionMap";
import { MapLegend } from "../components/map/MapLegend";

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

function periodBadge(period: ReplayPeriod): { text: string; tone: string } {
  if (period.status === "NO_JURISDICTION" || period.status === "INVALID_LOCATION") {
    return { text: "NO JURISDICTION", tone: STATUS_TONE[period.status] };
  }
  if (period.status === "RESPONSIBILITY_UNRESOLVED" || period.status === "TEMPORAL_CONFLICT") {
    return { text: "RESPONSIBILITY UNRESOLVED", tone: STATUS_TONE[period.status] };
  }
  if (period.version_status === "CURRENT") {
    return { text: "CURRENT", tone: "ok-tag" };
  }
  return { text: "HISTORICAL", tone: "muted-tag" };
}

function periodYear(period: ReplayPeriod): string {
  return (period.effective_from ?? "").slice(0, 4) || "—";
}

interface FieldDiff {
  field: string;
  oldValue: string;
  newValue: string;
}

function changesBetween(prev: ReplayPeriod, next: ReplayPeriod): FieldDiff[] {
  const diffs: FieldDiff[] = [];
  const pair = (field: string, a: string | null | undefined, b: string | null | undefined) => {
    if ((a ?? null) !== (b ?? null)) {
      diffs.push({ field, oldValue: a ?? "(none)", newValue: b ?? "(none)" });
    }
  };
  pair("Jurisdiction", prev.jurisdiction_code, next.jurisdiction_code);
  pair("Ward", prev.ward_code, next.ward_code);
  pair("Version", prev.version_code, next.version_code);
  pair("Authority", prev.authority?.code, next.authority?.code);
  pair("Department", prev.department?.code, next.department?.code);
  pair("Service", prev.service?.code, next.service?.code);
  pair("Rule", prev.routing_rule_code, next.routing_rule_code);
  return diffs;
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

  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [asOf, setAsOf] = useState<string | null>(null);
  const [jurisdictions, setJurisdictions] = useState<JurisdictionSummary[]>([]);
  const [areas, setAreas] = useState<AreaSummary[]>([]);
  const [roads, setRoads] = useState<RoadSummary[]>([]);
  const [gisLoading, setGisLoading] = useState(false);
  const [gisError, setGisError] = useState<string | null>(null);

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
    setSelectedIndex(null);
    setAsOf(null);
    fetchReplayPoint({
      latitude: latN,
      longitude: lngN,
      issue_type: issueCode,
      start_date: startD,
      end_date: endD,
    })
      .then((data) => {
        setState({ kind: "ok", data });
        if (data.periods.length > 0) {
          const latest = data.periods.length - 1;
          setSelectedIndex(latest);
          setAsOf(data.periods[latest].effective_from);
        }
      })
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

  useEffect(() => {
    if (!asOf) return;
    let cancelled = false;
    setGisLoading(true);
    setGisError(null);
    Promise.all([fetchJurisdictions({ date: asOf, includeGeometry: true }), fetchAreas(), fetchRoads()])
      .then(([jurisdictionResponse, areaResponse, roadResponse]) => {
        if (cancelled) return;
        setJurisdictions(jurisdictionResponse.jurisdictions);
        setAreas(areaResponse.areas);
        setRoads(roadResponse.roads);
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setGisError(error instanceof ApiError ? error.message : "Unknown error");
        }
      })
      .finally(() => {
        if (!cancelled) setGisLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [asOf]);

  const data = state.kind === "ok" ? state.data : null;
  const selectedPeriod: ReplayPeriod | null =
    data && selectedIndex !== null ? data.periods[selectedIndex] ?? null : null;

  const activeVersionLabels = useMemo(() => {
    const seen = new Set<string>();
    for (const j of jurisdictions) {
      if (j.version_status === "CURRENT") seen.add(`${j.version_code} · CURRENT`);
    }
    const labels = [...seen].slice(0, 2);
    if (asOf) labels.push(`As of ${asOf}`);
    return labels;
  }, [jurisdictions, asOf]);

  const handleSelect = (selectLat: number, selectLng: number) => {
    setLat(String(selectLat));
    setLng(String(selectLng));
  };

  const diffs = useMemo(() => {
    if (!data || selectedIndex === null || selectedIndex === 0) return [];
    return changesBetween(data.periods[selectedIndex - 1], data.periods[selectedIndex]);
  }, [data, selectedIndex]);

  return (
    <section className="page">
      <header className="page-header">
        <h1>Historical Jurisdiction Replay</h1>
        <p>
          Travel through jurisdiction history and see how responsibility changes over time.
          Each day is routed independently and identical outcomes are merged into periods.
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
          <label htmlFor="replay-issue">Issue type</label>
          <select id="replay-issue" value={issue} onChange={(e) => setIssue(e.target.value)}>
            {issueTypes.map((t) => (
              <option key={t.code} value={t.code}>
                {t.name} · {t.code}
              </option>
            ))}
          </select>
        </div>
        <div className="gis-toolbar-item">
          <label htmlFor="replay-start">Start date (inclusive)</label>
          <input id="replay-start" type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        </div>
        <div className="gis-toolbar-item">
          <label htmlFor="replay-end">End date (exclusive)</label>
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

          {data.period_count > 0 && (
            <div className="gis-layout">
              <div className="card gis-map-card">
                <h3>
                  Boundary layout <span className="muted">as of {asOf ?? data.start_date}</span>
                </h3>
                {gisError && <p className="error-text">{gisError}</p>}
                {gisLoading && <p className="muted">Loading boundary layout…</p>}
                {!gisLoading && !gisError && (
                  <JurisdictionMap
                    jurisdictions={jurisdictions}
                    areas={areas}
                    roads={roads}
                    probe={{ lat: data.latitude, lng: data.longitude }}
                    highlightCode={selectedPeriod?.jurisdiction_code ?? null}
                    activeVersionLabels={activeVersionLabels}
                    onSelect={handleSelect}
                  />
                )}
                {!gisLoading && !gisError && <MapLegend />}
                <p className="muted gis-click-hint">
                  Boundary shapes are fetched for the selected period's start date. Clicking the map
                  updates the location fields to replay a different point.
                </p>
              </div>

              <div className="card gis-result-card replay-inspector">
                <h3>Selected period</h3>
                {selectedPeriod ? (
                  <PeriodInspector period={selectedPeriod} />
                ) : (
                  <p className="muted">No period selected.</p>
                )}
              </div>
            </div>
          )}

          <div className="replay-timeline" role="list" aria-label="Jurisdiction history timeline">
            {data.periods.map((period, index) => {
              const prev = data.periods[index - 1];
              const changes = prev ? changesBetween(prev, period) : [];
              const badge = periodBadge(period);
              const isSelected = selectedIndex === index;
              return (
                <div key={`${period.effective_from}-${period.effective_to}`} className="replay-period">
                  <button
                    type="button"
                    className={`replay-node${isSelected ? " replay-node-selected" : ""}`}
                    aria-pressed={isSelected}
                    onClick={() => {
                      setSelectedIndex(index);
                      setAsOf(period.effective_from);
                    }}
                  >
                    <span className="replay-node-year">{periodYear(period)}</span>
                    <span className={`replay-node-badge ${badge.tone}`}>{badge.text}</span>
                    <span className="replay-node-range">
                      {period.effective_from} → {period.effective_to ?? "open"}
                    </span>
                  </button>

                  {index > 0 && (
                    <div className="boundary-marker" aria-label={`Boundary change before period ${index + 1}`}>
                      <span className="boundary-badge">● BOUNDARY CHANGE</span>
                      {changes.length > 0 && (
                        <span className="boundary-changes">
                          {changes.map((c) => `${c.field}: ${c.oldValue} → ${c.newValue}`).join(" · ")}
                        </span>
                      )}
                      {prev?.effective_to && <span className="boundary-date">at {prev.effective_to}</span>}
                    </div>
                  )}

                  <div className={`card replay-period-card${isSelected ? " replay-period-selected" : ""}`}>
                    <div className="module-head">
                      <span className="replay-period-range">
                        {period.effective_from} → {period.effective_to ?? "open"}
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

          {selectedPeriod && selectedIndex !== null && selectedIndex > 0 && (
            <div className="card replay-audit">
              <h3>What changed?</h3>
              {diffs.length > 0 ? (
                <div className="what-changed">
                  {diffs.map((d) => (
                    <div key={d.field} className="what-changed-row">
                      <span className="what-changed-field">{d.field}</span>
                      <span className="what-changed-old">{d.oldValue}</span>
                      <span className="what-changed-arrow" aria-hidden="true">→</span>
                      <span className="what-changed-new">{d.newValue}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="muted">
                  No routing fields change between {data.periods[selectedIndex - 1].effective_from} and{" "}
                  {selectedPeriod.effective_from} — the periods differ only in date coverage.
                </p>
              )}
            </div>
          )}

          <div className="card replay-audit">
            <p className="muted">
              Replay re-resolves responsibility independently for each date using the jurisdiction
              rules active during that period. The replay response does not carry a decision/audit ID.
            </p>
          </div>
        </div>
      )}
    </section>
  );
}

function chainStep({ icon, label, value }: { icon: string; label: string; value: string } ) {
  return (
    <li className="explain-node">
      <span className="explain-node-icon" aria-hidden="true">{icon}</span>
      <div className="explain-node-body">
        <span className="explain-node-label">{label}</span>
        <span className="explain-node-value">{value}</span>
      </div>
    </li>
  );
}

function PeriodInspector({ period }: { period: ReplayPeriod }) {
  const badge = periodBadge(period);
  return (
    <div className="replay-inspector-body">
      <div className="replay-inspector-head">
        <div>
          <h4>Responsibility on {period.effective_from}</h4>
          <p className="muted">
            {period.effective_from} → {period.effective_to ?? "open"} ·{" "}
            <span className={`result-status ${STATUS_TONE[period.status]}`}>{period.status}</span> ·{" "}
            <span className={badge.tone}>{badge.text}</span>
          </p>
        </div>
      </div>

      {period.status === "NO_JURISDICTION" && (
        <div className="replay-nostate">
          ⚠ No jurisdiction covered this location during this period.
        </div>
      )}
      {period.status === "RESPONSIBILITY_UNRESOLVED" && (
        <div className="replay-nostate replay-nostate-unresolved">
          Responsibility was unresolved during this period.
          {period.reason ? ` ${period.reason}` : ""}
          {period.conflict_rule_codes.length > 0 && (
            <ul className="conflict-list">
              {period.conflict_rule_codes.map((code) => (
                <li key={code}>
                  <code>{code}</code>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {period.status !== "NO_JURISDICTION" && period.status !== "RESPONSIBILITY_UNRESOLVED" && (
        <ol className="explain-chain">
          {chainStep({
            icon: "🗺",
            label: "Jurisdiction",
            value: period.jurisdiction_code
              ? `${period.jurisdiction_code}${period.jurisdiction_name ? ` · ${period.jurisdiction_name}` : ""}${period.version_code ? ` · ${period.version_code}${period.version_status ? ` (${period.version_status})` : ""}` : ""}`
              : "(none)",
          })}
          {chainStep({
            icon: "🗂",
            label: "Ward / Area",
            value: period.ward_code ? `${period.ward_code} · ${period.ward_name ?? ""}` : period.matched_scope ?? "(none)",
          })}
          {chainStep({
            icon: "🏛",
            label: "Authority",
            value: period.authority ? `${period.authority.name} · ${period.authority.code}` : "(none)",
          })}
          {chainStep({
            icon: "🏢",
            label: "Department",
            value: period.department ? `${period.department.name} · ${period.department.code}` : "(none)",
          })}
          {chainStep({
            icon: "🛠",
            label: "Service",
            value: period.service ? `${period.service.name} · ${period.service.code}` : "(none)",
          })}
          {chainStep({
            icon: "📋",
            label: "Routing Rule",
            value: period.routing_rule_code ? `${period.routing_rule_code}${period.routing_rule_id !== null ? ` · rule id #${period.routing_rule_id}` : ""}` : "(none)",
          })}
        </ol>
      )}

      {period.explanation && <p className="why-route">{period.explanation}</p>}
      {period.reason && <p className="muted">{period.reason}</p>}
    </div>
  );
}