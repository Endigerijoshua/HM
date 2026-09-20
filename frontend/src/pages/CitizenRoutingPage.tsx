import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ApiError, fetchAreas, fetchJurisdictions, fetchRoads, lookupJurisdiction } from "../api";
import type { AreaSummary, JurisdictionSummary, RoadSummary } from "../api/gisTypes";
import { resolveGraph } from "../api/graph";
import type { GraphResolveResponse } from "../api/graphTypes";
import { fetchIssueTypes, fetchRoutingRules, resolveRoute } from "../api/routing";
import type {
  IssueTypeSummary,
  RoutingResult,
  RoutingRuleSummary,
  RoutingStatus,
} from "../api/routingTypes";
import { ResponsibilityGraph } from "../components/graph/ResponsibilityGraph";
import { CivicMap } from "../components/map/CivicMap";
import { RoutingExplanation } from "../components/routing/RoutingExplanation";
import { DemoFlowBar } from "../components/DemoFlowBar";
import { useViewMode } from "../components/layout/ViewContext";
import { useCitizenLanguage } from "../lib/i18n/CitizenLanguage";
import { fill, strings, type Dict } from "../lib/i18n/citizenStrings";
import { useGeolocation } from "../hooks/useGeolocation";
import {
  isGeolocationSupported,
  type SelectedLocation,
} from "../lib/geolocation";

const MIN_DATE = "2020-01-01";
const MAX_DATE = "2026-12-31";
const DEFAULT_DATE = "2024-06-01";

const QUICK_DATES = [
  { label: "V1 · DELIM-2020", date: "2023-06-01" },
  { label: "Gap · no jurisdiction", date: "2024-01-05" },
  { label: "V2 · DELIM-2024", date: "2024-06-01" },
];

/** Deterministic demo points (verified in-force + resolve/conflict for 2024-06-01). */
const SCENARIOS = [
  {
    label: "Pothole · W-05",
    issue: "pothole",
    point: { lat: 12.3082, lng: 76.6438 },
  },
  {
    label: "Heritage maintenance · W-05",
    issue: "heritage_maintenance",
    point: { lat: 12.3125, lng: 76.635 },
  },
  {
    label: "Garbage collection · V1/V2 flip",
    issue: "garbage_collection",
    point: { lat: 12.279255877741852, lng: 76.60731308845853 },
  },
  {
    label: "Construction waste · unresolved",
    issue: "construction_waste",
    point: { lat: 12.3125, lng: 76.635 },
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
  const { view } = useViewMode();
  const { lang } = useCitizenLanguage();
  const dict = strings[view === "admin" ? "en" : lang];

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
  const [graph, setGraph] = useState<GraphResolveResponse | null>(null);
  const [graphError, setGraphError] = useState<string | null>(null);

  const [selectedLocation, setSelectedLocation] = useState<SelectedLocation | null>(null);
  const [focusLocation, setFocusLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [manualLat, setManualLat] = useState("");
  const [manualLng, setManualLng] = useState("");
  const [manualError, setManualError] = useState<string | null>(null);
  const [gpsOutside, setGpsOutside] = useState(false);
  const geo = useGeolocation();

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
      setGraphError(null);
      setGraph(null);
      resolveRoute({ lat, lng, issue_type: issue, date })
        .then((res) => {
          setProbe({ lat: res.latitude, lng: res.longitude });
          setResult(res);
        })
        .catch((error: unknown) =>
          setResultError(error instanceof ApiError ? error.message : "Unknown error"),
        )
        .finally(() => setResolving(false));
      resolveGraph({ lat, lng, issue_type: issue, date })
        .then(setGraph)
        .catch((error: unknown) =>
          setGraphError(error instanceof ApiError ? error.message : "Unknown error"),
        );
    },
    [],
  );

  const applyGps = useCallback(() => {
    geo.requestLocation({ enableHighAccuracy: true, timeout: 10000, maximumAge: 0 });
  }, [geo]);

  useEffect(() => {
    if (geo.status !== "success" || geo.latitude == null || geo.longitude == null) return;
    const { latitude, longitude, accuracy } = geo;
    setSelectedLocation({ latitude, longitude, accuracy, source: "gps" });
    setFocusLocation({ lat: latitude, lng: longitude });
    setGpsOutside(false);
    let cancelled = false;
    lookupJurisdiction({ lat: latitude, lng: longitude, on_date: onDate })
      .then((lookup) => {
        if (cancelled) return;
        setGpsOutside(lookup.status !== "MATCHED");
      })
      .catch(() => {
        if (!cancelled) setGpsOutside(false);
      });
    return () => {
      cancelled = true;
    };
  }, [geo.status, geo.latitude, geo.longitude, geo.accuracy, onDate]);

  const handleSelect = useCallback(
    (lat: number, lng: number) => {
      setSelectedLocation({ latitude: lat, longitude: lng, accuracy: null, source: "map" });
      setGpsOutside(false);
      geo.reset();
      if (issueType) runResolve(lat, lng, issueType, onDate);
    },
    [geo, issueType, onDate, runResolve],
  );

  const applyManual = () => {
    const lat = Number(manualLat);
    const lng = Number(manualLng);
    if (!Number.isFinite(lat) || lat < -90 || lat > 90) {
      setManualError(dict.latError);
      return;
    }
    if (!Number.isFinite(lng) || lng < -180 || lng > 180) {
      setManualError(dict.lngError);
      return;
    }
    setManualError(null);
    setSelectedLocation({ latitude: lat, longitude: lng, accuracy: null, source: "manual" });
    setFocusLocation({ lat, lng });
    setGpsOutside(false);
    geo.reset();
  };

  const [searchParams] = useSearchParams();
  const demoMode = searchParams.get("demo") === "1";
  const demoRun = useRef(false);

  useEffect(() => {
    if (demoRun.current || !demoMode) return;
    const lat = Number(searchParams.get("lat"));
    const lng = Number(searchParams.get("lng"));
    const issue = searchParams.get("issue");
    if (!Number.isFinite(lat) || !Number.isFinite(lng) || !issue) return;
    demoRun.current = true;
    setIssueType(issue);
    const date = searchParams.get("date");
    if (date) setOnDate(date);
    setSelectedLocation({ latitude: lat, longitude: lng, accuracy: null, source: "map" });
    setFocusLocation({ lat, lng });
    setGpsOutside(false);
    runResolve(lat, lng, issue, date ?? onDate);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [demoMode]);

  const handleScenario = (issue: string, point: { lat: number; lng: number }) => {
    setIssueType(issue);
    setSelectedLocation({ latitude: point.lat, longitude: point.lng, accuracy: null, source: "map" });
    setFocusLocation({ lat: point.lat, lng: point.lng });
    setGpsOutside(false);
    runResolve(point.lat, point.lng, issue, onDate);
  };

  const categories = Array.from(new Set(issueTypes.map((t) => t.category))).sort();
  const highlightCode = result?.jurisdiction_code ?? null;

  return (
    <section className="page citizen-page">
      <header className="page-header citizen-header">
        <h1>{dict.pageTitle}</h1>
        <p>{dict.pageSubtitle}</p>
      </header>

      {view === "admin" && demoMode && <DemoFlowBar active="route" />}

      {state.kind === "error" && <p className="error-text">{state.message}</p>}
      {state.kind === "loading" && <p className="muted">{dict.loadingData}</p>}

      <section className="route-step">
        <div className="route-step-head">
          <span className="route-step-no">1</span>
          <h2>{dict.stepDescribe}</h2>
        </div>
        <div className="route-inputs">
          <div className="route-field">
            <label htmlFor="issue-type">{dict.issueTypeLabel}</label>
            <select
              id="issue-type"
              value={issueType}
              onChange={(event) => setIssueType(event.target.value)}
            >
              <option value="">{dict.issuePlaceholder}</option>
              {categories.map((category) => (
                <optgroup key={category} label={dict.categoryNames[category] ?? category}>
                  {issueTypes
                    .filter((t) => t.category === category)
                    .map((t) => (
                      <option key={t.code} value={t.code}>
                        {dict.issueTypeNames[t.code] ?? t.name} · {t.code}
                      </option>
                    ))}
                </optgroup>
              ))}
            </select>
          </div>
          <div className="route-field">
            <label htmlFor="on-date">{dict.onDateLabel}</label>
            <input
              id="on-date"
              type="date"
              min={MIN_DATE}
              max={MAX_DATE}
              value={onDate}
              onChange={(event) => setOnDate(event.target.value)}
            />
          </div>
        </div>
        {state.kind === "ok" && (
          <p className="muted route-count">
            {fill(dict.jurisdictionCount, { count: jurisdictions.length, date: onDate })}
          </p>
        )}
        <details className="route-presets">
          <summary>{dict.presetsSummary}</summary>
          <div className="route-presets-grid">
            <div className="route-presets-col">
              <span className="route-presets-label">{dict.presetsDatesLabel}</span>
              <div className="gis-quick">
                {QUICK_DATES.map((q) => (
                  <button key={q.date} className="chip" onClick={() => setOnDate(q.date)}>
                    {dict.quickDates[q.date] ?? q.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="route-presets-col">
              <span className="route-presets-label">{dict.presetsScenariosLabel}</span>
              <div className="gis-quick">
                {SCENARIOS.map((s) => (
                  <button
                    key={s.label}
                    className="chip"
                    onClick={() => handleScenario(s.issue, s.point)}
                  >
                    {dict.scenarios[s.label] ?? s.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </details>
      </section>

      <section className="route-step">
        <div className="route-step-head">
          <span className="route-step-no">2</span>
          <h2>{dict.stepPinLocation}</h2>
        </div>

        <div className="routing-location-row">
          <button
            type="button"
            className="btn btn-primary btn-lg routing-gps-btn"
            onClick={applyGps}
            disabled={geo.status === "requesting" || !isGeolocationSupported()}
            aria-label={dict.gpsIdle}
          >
            {geo.status === "requesting" ? dict.gpsRequesting : dict.gpsIdle}
          </button>
        </div>

        <div className="location-panel" aria-live="polite">
          {geo.status === "requesting" && <p className="location-status">{dict.gpsRequesting}</p>}
          {geo.error && geo.status !== "requesting" && geo.status !== "success" && (
            <div className="location-error">
              <p>{geo.error}</p>
              {isGeolocationSupported() && (
                <button type="button" className="btn btn-outline btn-sm" onClick={applyGps}>
                  {dict.tryAgain}
                </button>
              )}
            </div>
          )}
          {selectedLocation && geo.status !== "requesting" && !geo.error && (
            <p className="location-status">
              <span className="location-source">
                {fill(dict.locationFrom, { source: locationSourceLabel(selectedLocation.source, dict) })}
              </span>
              : {selectedLocation.latitude.toFixed(5)}, {selectedLocation.longitude.toFixed(5)}
              {selectedLocation.accuracy != null
                ? ` ${fill(dict.accuracyTemplate, { accuracy: Math.round(selectedLocation.accuracy) })}`
                : ""}
            </p>
          )}
          {gpsOutside && selectedLocation?.source === "gps" && (
            <p className="location-outside">{dict.gpsOutside}</p>
          )}
          {!selectedLocation && geo.status !== "requesting" && !geo.error && (
            <p className="muted">{dict.emptyLocationHint}</p>
          )}
        </div>

        <div className="route-map-card">
          <CivicMap
            jurisdictions={jurisdictions}
            areas={areas}
            roads={roads}
            probe={probe}
            highlightCode={highlightCode}
            activeVersionLabels={activeVersions}
            selectedLocation={selectedLocation}
            focusLocation={focusLocation}
            onSelect={handleSelect}
          />
          <p className="muted gis-click-hint">
            {issueType
              ? fill(dict.mapHintRoute, { issueType, onDate })
              : dict.mapHintChooseIssue}
          </p>
        </div>

        <details className="manual-coords">
          <summary>{dict.manualSummary}</summary>
          <div className="manual-coords-grid">
            <div className="field">
              <label htmlFor="manual-lat">{dict.latitude}</label>
              <input
                id="manual-lat"
                type="number"
                step="any"
                min="-90"
                max="90"
                placeholder="e.g. 12.3125"
                value={manualLat}
                onChange={(event) => setManualLat(event.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="manual-lng">{dict.longitude}</label>
              <input
                id="manual-lng"
                type="number"
                step="any"
                min="-180"
                max="180"
                placeholder="e.g. 76.635"
                value={manualLng}
                onChange={(event) => setManualLng(event.target.value)}
              />
            </div>
            <button type="button" className="btn btn-outline manual-set-btn" onClick={applyManual}>
              {dict.setLocation}
            </button>
          </div>
          {manualError && <p className="error-text">{manualError}</p>}
          <p className="muted">{dict.manualHint}</p>
        </details>

        <div className="routing-resolve-row route-resolve-row">
          <button
            type="button"
            className="btn btn-primary btn-lg routing-resolve-btn"
            disabled={!selectedLocation || !issueType || resolving}
            onClick={() => {
              if (!selectedLocation) return;
              runResolve(selectedLocation.latitude, selectedLocation.longitude, issueType, onDate);
            }}
          >
            {resolving ? dict.resolveBusy : dict.resolveIdle}
          </button>
          {(!selectedLocation || !issueType) && (
            <p className="muted routing-resolve-hint">
              {!issueType ? dict.resolveHintNoIssue : dict.resolveHintNoLocation}
            </p>
          )}
        </div>
      </section>

      <section className="route-step route-result-step" aria-live="polite">
        <div className="route-step-head">
          <span className="route-step-no">3</span>
          <h2>{dict.stepResponsible}</h2>
        </div>
        {resolving && <p className="muted">{dict.resolveBusy}</p>}
        {resultError && <p className="error-text">{resultError}</p>}
        {!resolving && !resultError && !result && (
          <p className="muted route-result-empty">{dict.resultEmpty}</p>
        )}
        {!resolving && !resultError && result && (
          <div className="route-result-card">
            <RoutingResultView result={result} dict={dict} />
            <RoutingExplanation result={result} dict={dict} />
            <details className="route-extra">
              <summary>{dict.routeExtraSummary}</summary>
              <div className="replay-links">
                <Link
                  className="btn btn-outline"
                  to={`/replay?lat=${result.latitude}&lng=${result.longitude}&issue=${encodeURIComponent(result.issue_type)}&start=2023-01-01&end=2025-01-01`}
                >
                  {dict.replayLink}
                </Link>
                <Link
                  className="btn btn-outline"
                  to={`/history?lat=${result.latitude}&lng=${result.longitude}`}
                >
                  {dict.historyLink}
                </Link>
              </div>
            </details>
          </div>
        )}
      </section>

      <details className="route-advanced">
        <summary>{dict.advancedSummary}</summary>
        {graphError && <p className="error-text">{graphError}</p>}
        {graph && (
          <div className="card resp-graph-card">
            <div className="resp-graph-head">
              <h3>{dict.advancedWhyRoute}</h3>
              {graph.routing_id !== null && (
                <span className="muted">{fill(dict.auditRouting, { id: graph.routing_id })}</span>
              )}
            </div>
            <p className="resp-graph-status">
              {dict.routingStatus}{" "}
              <span
                className={`result-status ${
                  (STATUS_TONE as Record<string, string>)[graph.status] ?? "muted-tag"
                }`}
              >
                {graph.status}
              </span>
            </p>
            <p className="why-route">{graph.explanation}</p>
            <ResponsibilityGraph data={graph} />
          </div>
        )}

        {rules.length > 0 && (
          <div className="card rules-card">
            <h3>
              {fill(dict.rulesCount, { count: rules.length, issue: issueType, date: onDate })}
            </h3>
            <div className="table-scroll rules-table-wrap">
              <table className="rules-table">
              <thead>
                <tr>
                  <th>{dict.tableRule}</th>
                  <th>{dict.tableScope}</th>
                  <th>{dict.tablePrio}</th>
                  <th>{dict.tableInForce}</th>
                  <th>{dict.tableAuthorityService}</th>
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
          </div>
        )}
      </details>
    </section>
  );
}

function locationSourceLabel(source: SelectedLocation["source"], dict: Dict): string {
  if (source === "gps") return dict.sourceGps;
  if (source === "map") return dict.sourceMap;
  return dict.sourceManual;
}

function RoutingResultView({ result, dict }: { result: RoutingResult; dict: Dict }) {
  return (
    <div className="gis-result">
      <div className="module-head">
        <span className={`result-status ${STATUS_TONE[result.status]}`}>{result.status}</span>
      </div>

      {result.status === "NO_JURISDICTION" && (
        <div className="no-jurisdiction-note" role="status">
          {dict.resultNoJurisdiction}
        </div>
      )}

      <dl className="kv">
        <div>
          <dt>{dict.resultPoint}</dt>
          <dd>
            {result.latitude.toFixed(5)}, {result.longitude.toFixed(5)}
          </dd>
        </div>
        <div>
          <dt>{dict.resultIssue}</dt>
          <dd>{result.issue_type}</dd>
        </div>
        <div>
          <dt>{dict.resultDate}</dt>
          <dd>{result.effective_date}</dd>
        </div>
        {result.jurisdiction_code && (
          <div>
            <dt>{dict.resultJurisdiction}</dt>
            <dd>
              {result.jurisdiction_code} · {result.jurisdiction_kind ?? "?"}
            </dd>
          </div>
        )}
        {result.ward_code && (
          <div>
            <dt>{dict.resultWard}</dt>
            <dd>
              {result.ward_code} · {result.ward_name ?? ""}
            </dd>
          </div>
        )}
        {result.version_code && (
          <div>
            <dt>{dict.resultVersion}</dt>
            <dd>{result.version_code}</dd>
          </div>
        )}
      </dl>

      {result.status === "RESOLVED" && result.authority && result.department && result.service && (
        <>
          <div className="actor-chain">
            <DirectorActor label={dict.actorAuthority} actor={result.authority} />
            <span className="actor-arrow">→</span>
            <DirectorActor label={dict.actorDepartment} actor={result.department} />
            <span className="actor-arrow">→</span>
            <DirectorActor label={dict.actorService} actor={result.service} />
          </div>
          <dl className="kv">
            {result.matched_scope && (
              <div>
                <dt>{dict.resultMatchedScope}</dt>
                <dd>{result.matched_scope}</dd>
              </div>
            )}
            {result.sla_days !== null && (
              <div>
                <dt>{dict.resultSla}</dt>
                <dd>{result.sla_days} {dict.slaUnit}</dd>
              </div>
            )}
            {result.routing_rule_code && (
              <div>
                <dt>{dict.resultRule}</dt>
                <dd>
                  <code>{result.routing_rule_code}</code>
                </dd>
              </div>
            )}
          </dl>
          {result.escalation_path.length > 0 && (
            <div className="escalation">
              <h4>{dict.resultEscalationPath}</h4>
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
          <h4>{dict.resultConflictTitle}</h4>
          <p>{dict.resultConflictBody}</p>
          <ul className="conflict-list">
            {result.conflict_rule_codes.map((code) => (
              <li key={code}>
                <code>{code}</code>
              </li>
            ))}
          </ul>
          <p className="muted">{dict.resultConflictNote}</p>
        </div>
      )}

      {result.explanation && <p className="why-route">{result.explanation}</p>}
      {result.reason && <p className="muted">{result.reason}</p>}
      {result.audit_id !== null && (
        <p className="muted">{fill(dict.resultAudit, { id: result.audit_id })}</p>
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