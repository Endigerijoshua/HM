import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, fetchAreas, fetchJurisdictions, fetchRoads } from "../api";
import type {
  AreaSummary,
  GeoJsonGeometry,
  JurisdictionSummary,
  RoadSummary,
} from "../api/gisTypes";
import { fetchMigrationPreview } from "../api/migrations";
import type {
  MigrationComplaint,
  MigrationPreviewResponse,
} from "../api/migrationTypes";
import { fetchWhatIfScenarios, simulateWhatIf } from "../api/whatif";
import type {
  ImpactMetric,
  WhatIfScenarioSummary,
  WhatIfSimulateResponse,
} from "../api/whatifTypes";
import type { RoutingResult } from "../api/routingTypes";
import { JurisdictionMap } from "../components/map/JurisdictionMap";
import { MapLegend } from "../components/map/MapLegend";

const ON_DATE = "2026-09-18";

type MapView = "current" | "proposed" | "difference";

interface QuickScenario {
  label: string;
  code: string;
  point: { lon: number; lat: number };
  issue: string;
}

/** Deterministic quick flips (seeded demo geometry, no live mutation). */
const QUICK_SCENARIOS: QuickScenario[] = [
  {
    label: "Heritage expansion · inside rezone",
    code: "SC-V3-REZONE",
    point: { lon: 76.6438, lat: 12.3082 },
    issue: "heritage_maintenance",
  },
  {
    label: "Heritage core · outside rezone",
    code: "SC-V3-REZONE",
    point: { lon: 76.635, lat: 12.33 },
    issue: "heritage_maintenance",
  },
  {
    label: "Flip point · V1/V2",
    code: "SC-V3-REZONE",
    point: { lon: 76.60731308845853, lat: 12.279255877741852 },
    issue: "garbage_collection",
  },
  {
    label: "Heritage boundary flip · responsibility change",
    code: "SC-V3-REZONE",
    point: { lon: 76.655, lat: 12.31 },
    issue: "heritage_maintenance",
  },
];

function deltaText(delta: number, unit: string): string {
  if (delta === 0) return "unchanged";
  return `${delta > 0 ? "+" : ""}${delta} ${unit}`;
}

function areaMetric(result: WhatIfSimulateResponse): ImpactMetric | undefined {
  return result.impact.find((m) => m.label === "Heritage precinct area (km2)");
}

function conflictCount(result: WhatIfSimulateResponse): number {
  return result.potential_conflicts.filter((c) => c && c !== "NONE").length;
}

export default function WhatIfSimulatorPage() {
  const [state, setState] = useState<{ kind: "loading" } | { kind: "ok" } | { kind: "error"; message: string }>({ kind: "loading" });
  const [gisState, setGisState] = useState<{ kind: "loading" } | { kind: "ok" } | { kind: "error"; message: string }>({ kind: "loading" });
  const [jurisdictions, setJurisdictions] = useState<JurisdictionSummary[]>([]);
  const [areas, setAreas] = useState<AreaSummary[]>([]);
  const [roads, setRoads] = useState<RoadSummary[]>([]);
  const [scenario, setScenario] = useState<WhatIfScenarioSummary | null>(null);
  const [scenarios, setScenarios] = useState<WhatIfScenarioSummary[]>([]);
  const [lon, setLon] = useState("76.6438");
  const [lat, setLat] = useState("12.3082");
  const [issue, setIssue] = useState("heritage_maintenance");
  const [simulating, setSimulating] = useState(false);
  const [result, setResult] = useState<WhatIfSimulateResponse | null>(null);
  const [resultError, setResultError] = useState<string | null>(null);
  const [view, setView] = useState<MapView>("current");
  const [probePoint, setProbePoint] = useState<{ lat: number; lng: number } | null>(null);
  const [preview, setPreview] = useState<MigrationPreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setState({ kind: "loading" });
    fetchWhatIfScenarios()
      .then((response) => {
        if (cancelled) return;
        setScenarios(response.scenarios);
        setScenario(response.scenarios[0] ?? null);
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
    setGisState({ kind: "loading" });
    Promise.all([fetchJurisdictions({ date: ON_DATE, includeGeometry: true }), fetchAreas(), fetchRoads()])
      .then(([jurisdictionResponse, areaResponse, roadResponse]) => {
        if (cancelled) return;
        setJurisdictions(jurisdictionResponse.jurisdictions);
        setAreas(areaResponse.areas);
        setRoads(roadResponse.roads);
        setGisState({ kind: "ok" });
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setGisState({
            kind: "error",
            message: error instanceof ApiError ? error.message : "Unknown error",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const loadPreview = useCallback((scenarioCode: string) => {
    setPreviewLoading(true);
    setPreviewError(null);
    fetchMigrationPreview(scenarioCode)
      .then((response) => setPreview(response))
      .catch((error: unknown) => {
        setPreviewError(error instanceof ApiError ? error.message : "Unknown error");
        setPreview(null);
      })
      .finally(() => setPreviewLoading(false));
  }, []);

  const runSimulate = useCallback(
    (lng: number, latValue: number, issueType: string) => {
      setSimulating(true);
      setResultError(null);
      setResult(null);
      setPreview(null);
      setPreviewError(null);
      setProbePoint({ lat: latValue, lng });
      simulateWhatIf({
        longitude: lng,
        latitude: latValue,
        issue_type_code: issueType,
        on_date: ON_DATE,
      })
        .then((res) => {
          setResult(res);
          loadPreview(res.scenario_code);
        })
        .catch((error: unknown) =>
          setResultError(error instanceof ApiError ? error.message : "Unknown error"),
        )
        .finally(() => setSimulating(false));
    },
    [loadPreview],
  );

  const handleQuick = (quick: QuickScenario) => {
    setLon(String(quick.point.lon));
    setLat(String(quick.point.lat));
    setIssue(quick.issue);
    runSimulate(quick.point.lon, quick.point.lat, quick.issue);
  };

  const handleSelect = (selectLat: number, selectLng: number) => {
    setLon(String(selectLng));
    setLat(String(selectLat));
    setProbePoint({ lat: selectLat, lng: selectLng });
  };

  const activeVersions = useMemo(() => {
    const seen = new Set<string>();
    for (const j of jurisdictions) {
      if (j.version_status === "CURRENT") seen.add(`${j.version_code} · CURRENT`);
    }
    return [...seen].slice(0, 2);
  }, [jurisdictions]);

  const probe = probePoint ?? (result ? { lat: result.current.latitude, lng: result.current.longitude } : null);
  const highlightCode = result ? result.current.jurisdiction_code : null;
  const showProposed = view !== "current" && scenario ? (scenario.geometry_geojson as GeoJsonGeometry | null) : null;

  return (
    <section className="page">
      <header className="page-header">
        <h1>What-If Jurisdiction Simulator</h1>
        <p>
          Explore the impact of a proposed boundary change without modifying live jurisdiction
          data.
        </p>
        <div className="sim-only-badge">SIMULATION ONLY • LIVE DATA UNCHANGED</div>
      </header>

      <div className="gis-toolbar">
        <div className="gis-quick">
          {QUICK_SCENARIOS.map((quick) => (
            <button key={quick.label} className="chip" onClick={() => handleQuick(quick)}>
              {quick.label}
            </button>
          ))}
          <span className="scenario-select-label">Scenario:</span>
          <select
            value={scenario?.code ?? ""}
            onChange={(event) =>
              setScenario(scenarios.find((s) => s.code === event.target.value) ?? null)
            }
          >
            {scenarios.map((s) => (
              <option key={s.code} value={s.code}>
                {s.code} · {s.name}
              </option>
            ))}
          </select>
        </div>
        <div className="gis-date">{ON_DATE}</div>
      </div>

      {state.kind === "error" && <p className="error-text">{state.message}</p>}
      {state.kind === "loading" && <p className="muted">Loading scenarios…</p>}

      <div className="gis-layout">
        <div className="card gis-map-card">
          <div className="map-mode-chips" role="group" aria-label="Map view">
            <button
              type="button"
              className={`chip ${view === "current" ? "chip-active" : ""}`}
              aria-pressed={view === "current"}
              onClick={() => setView("current")}
            >
              Current
            </button>
            <button
              type="button"
              className={`chip ${view === "proposed" ? "chip-active" : ""}`}
              aria-pressed={view === "proposed"}
              onClick={() => setView("proposed")}
            >
              Proposed
            </button>
            <button
              type="button"
              className={`chip ${view === "difference" ? "chip-active" : ""}`}
              aria-pressed={view === "difference"}
              onClick={() => setView("difference")}
            >
              Difference
            </button>
          </div>

          {gisState.kind === "error" && <p className="error-text">{gisState.message}</p>}
          {gisState.kind === "loading" && <p className="muted">Loading map layout…</p>}
          {gisState.kind === "ok" && (
            <JurisdictionMap
              jurisdictions={jurisdictions}
              areas={areas}
              roads={roads}
              probe={probe}
              highlightCode={highlightCode}
              activeVersionLabels={activeVersions}
              proposedGeometry={showProposed}
              proposedLabel={showProposed && scenario ? `PROPOSED · ${scenario.code}` : null}
              onSelect={handleSelect}
            />
          )}
          {gisState.kind === "ok" && <MapLegend showProposed={showProposed != null} />}

          <p className="muted gis-click-hint">
            {view === "current" && "Live layout. Click the map to set a probe point, then press Simulate."}
            {view === "proposed" && scenario && (
              <>
                Live layout plus the dashed violet boundary of proposed scenario{" "}
                <code>{scenario.code}</code>. Click the map to set a probe point.
              </>
            )}
            {view === "difference" && (
              <>
                Proposed overlay (dashed violet) on top of the live layout; the quantified change
                comes from the last simulation below.
              </>
            )}
          </p>

          {view === "difference" && result && (
            <div className="diff-readout" aria-label="Simulated difference">
              {areaMetric(result) ? (
                <span>
                  Area: {areaMetric(result)?.current} → {areaMetric(result)?.proposed} km²
                </span>
              ) : null}
              <span>Complaints affected: {result.affected_complaint_count}</span>
              <span>Complaints switching responsibility: {result.responsibility_change_count}</span>
              <span>Probe changes: {result.responsibility_deltas.length}</span>
              <span>Conflicts: {conflictCount(result)}</span>
            </div>
          )}
        </div>

        <div className="card gis-form-card">
          <h3>Probe point</h3>
          <label htmlFor="whatif-lon">Longitude</label>
          <input
            id="whatif-lon"
            type="number"
            step="0.000001"
            value={lon}
            onChange={(event) => setLon(event.target.value)}
          />
          <label htmlFor="whatif-lat">Latitude</label>
          <input
            id="whatif-lat"
            type="number"
            step="0.000001"
            value={lat}
            onChange={(event) => setLat(event.target.value)}
          />
          <label htmlFor="whatif-issue">Issue</label>
          <select id="whatif-issue" value={issue} onChange={(event) => setIssue(event.target.value)}>
            <option value="heritage_maintenance">Heritage maintenance</option>
            <option value="garbage_collection">Garbage collection</option>
            <option value="garbage">Garbage (legacy)</option>
            <option value="pothole">Pothole</option>
            <option value="construction_waste">Construction waste</option>
          </select>
          <button
            disabled={simulating || state.kind !== "ok"}
            onClick={() => {
              const lngN = Number(lon);
              const latN = Number(lat);
              if (Number.isFinite(lngN) && Number.isFinite(latN)) runSimulate(lngN, latN, issue);
            }}
          >
            {simulating ? "Simulating…" : "Simulate"}
          </button>
          <p className="muted">Strictly read-only: no live jurisdiction is mutated.</p>
        </div>
      </div>

      {simulating && <p className="muted">Simulating responsibility…</p>}
      {resultError && <p className="error-text">{resultError}</p>}
      {!simulating && !resultError && !result && (
        <p className="muted">Pick a quick flip or enter a probe point to simulate a what-if.</p>
      )}

      {!simulating && !resultError && result && (
        <>
          <ResultSummaryCards result={result} />
          <CurrentVsProposed result={result} />
          <WhyItMatters result={result} preview={preview} />
          <ImpactDetails
            result={result}
            scenario={scenario}
            preview={preview}
            previewLoading={previewLoading}
            previewError={previewError}
          />
          <SimulationSafety scenario={scenario} />
        </>
      )}
    </section>
  );
}

function ResultSummaryCards({ result }: { result: WhatIfSimulateResponse }) {
  const area = areaMetric(result);
  const conflicts = conflictCount(result);
  const probeChanges = result.responsibility_deltas.length;
  return (
    <div className="impact-cards" aria-label="Simulation result summary">
      <div className="impact-card">
        <span className="impact-card-label">Affected complaints</span>
        <span className="impact-card-value">{result.affected_complaint_count}</span>
        <span className="impact-card-sub">
          complaints whose registered coordinates fall under the proposed boundary
        </span>
      </div>
      <div className="impact-card">
        <span className="impact-card-label">Responsibility changes</span>
        <span className="impact-card-value">{result.responsibility_change_count}</span>
        <span className="impact-card-sub">
          complaints whose department/service responsibility would change
        </span>
      </div>
      <div className="impact-card">
        <span className="impact-card-label">Probe responsibility changes</span>
        <span className="impact-card-value">{probeChanges}</span>
        <span className="impact-card-sub">
          assumption changes at this probe point (not complaint counts)
        </span>
      </div>
      {result.in_proposed_geometry && area && (
        <div className="impact-card">
          <span className="impact-card-label">Proposed precinct area</span>
          <span className="impact-card-value">
            {area.current} → {area.proposed} km²
          </span>
          <span className="impact-card-sub">{deltaText(area.delta, "km²")}</span>
        </div>
      )}
      <div className="impact-card">
        <span className="impact-card-label">Responsibility conflicts</span>
        <span className="impact-card-value">{conflicts}</span>
        <span className="impact-card-sub">
          {conflicts ? result.potential_conflicts.filter((c) => c !== "NONE").join(", ") : "none detected"}
        </span>
      </div>
    </div>
  );
}

function Strip({ label, code, name, status }: { label: string; code: string | null; name: string | null; status?: string }) {
  return (
    <div className="strip-item">
      <span className="strip-label">{label}</span>
      <span className="strip-value">
        {code ? (
          <>
            <code>{code}</code>
            {name ? <em> · {name}</em> : null}
          </>
        ) : (
          "—"
        )}
      </span>
      {status ? <span className="strip-status">{status}</span> : null}
    </div>
  );
}

function RoutingStripSet({ r }: { r: RoutingResult }) {
  return (
    <>
      <Strip
        label="Jurisdiction"
        code={r.jurisdiction_code}
        name={r.jurisdiction_name}
        status={r.jurisdiction_kind ?? undefined}
      />
      <Strip label="Ward" code={r.ward_code} name={r.ward_name} />
      <Strip label="Version" code={r.version_code} name={r.version_status} />
      <Strip label="Authority" code={r.authority?.code ?? null} name={r.authority?.name ?? null} />
      <Strip label="Department" code={r.department?.code ?? null} name={r.department?.name ?? null} />
      <Strip label="Service" code={r.service?.code ?? null} name={r.service?.name ?? null} />
      <Strip
        label="Matched scope"
        code={r.matched_scope}
        name={null}
        status={r.status !== "RESOLVED" ? r.status : undefined}
      />
    </>
  );
}

function CurrentVsProposed({ result }: { result: WhatIfSimulateResponse }) {
  const identical =
    !!result.proposed &&
    result.current.jurisdiction_code === result.proposed.jurisdiction_code &&
    result.current.ward_code === result.proposed.ward_code &&
    result.current.department?.code === result.proposed.department?.code &&
    result.current.service?.code === result.proposed.service?.code;

  return (
    <div className="card whatif-compare">
      <h3>Current vs Proposed</h3>
      <p className="muted">
        Scenario <code>{result.scenario_code}</code> · {result.scenario_name} · on{" "}
        <code>{result.on_date}</code>
      </p>
      <div className="ba-compare">
        <div className="card ba-card">
          <h4>
            Current boundary <span className="muted">(live)</span>
          </h4>
          <RoutingStripSet r={result.current} />
        </div>
        <div className="ba-arrow">
          <span aria-hidden="true">↓</span>
          <span className="muted">SIMULATE</span>
        </div>
        <div className="card ba-card proposed">
          <h4>
            Proposed boundary <span className="muted">(scenario)</span>
          </h4>
          {result.proposed ? (
            <RoutingStripSet r={result.proposed} />
          ) : (
            <p className="muted">No routing resolves under the proposed boundary.</p>
          )}
        </div>
      </div>
      {identical ? (
        <p className="muted">
          Routing details are unchanged at this point; the change is jurisdictional scope, shown
          under Impact details (responsibility deltas).
        </p>
      ) : null}
      {result.responsibility_deltas.length > 0 && (
        <p className="muted">
          Probe responsibility assumption: {result.responsibility_deltas[0].matched_scope ?? "changed"} —{" "}
          {result.responsibility_deltas[0].description}
        </p>
      )}
    </div>
  );
}

function WhyItMatters({
  result,
  preview,
}: {
  result: WhatIfSimulateResponse;
  preview: MigrationPreviewResponse | null;
}) {
  const area = areaMetric(result);
  const conflicts = conflictCount(result);
  const affected = result.affected_complaint_count;
  const changes = result.responsibility_change_count;
  const total = preview?.total_open_complaints;
  const withoutResponsibilityChange = affected - changes;
  const points: string[] = [
    `Simulating ${result.scenario_code} · ${result.scenario_name} on ${result.on_date}.`,
    `The probe point (${result.current.latitude.toFixed(4)}, ${result.current.longitude.toFixed(4)}) is ${
      result.in_proposed_geometry ? "inside" : "outside"
    } the proposed boundary of ${result.scenario_code}.`,
  ];
  if (area && result.in_proposed_geometry) {
    points.push(
      `Proposed precinct area changes from ${area.current} km² to ${area.proposed} km² (${deltaText(area.delta, "km²")}).`,
    );
  }
  if (affected > 0) {
    points.push(
      total != null && total > 0
        ? `${affected} of ${total} open complaints are affected by the proposed boundary; ${changes} would change civic responsibility.`
        : `${affected} open complaint${affected === 1 ? "" : "s"} ${affected === 1 ? "is" : "are"} affected by the proposed boundary; ${changes} would change civic responsibility.`,
    );
  }
  if (affected > 0 && withoutResponsibilityChange > 0) {
    points.push(
      `${withoutResponsibilityChange} affected complaint${
        withoutResponsibilityChange === 1 ? "" : "s"
      } ${withoutResponsibilityChange === 1 ? "remains" : "remain"} with the same department/service responsibility despite moving to the proposed jurisdiction.`,
    );
  }
  if (result.responsibility_deltas.length > 0) {
    points.push(
      `${result.responsibility_deltas.length} responsibility mapping${
        result.responsibility_deltas.length === 1 ? "" : "s"
      } change at the probe point.`,
    );
  }
  points.push(
    `${conflicts} responsibility conflict${conflicts === 1 ? "" : "s"} detected.`,
  );
  points.push(
    "Live jurisdiction data remains unchanged — the scenario is a read-only proposal.",
  );

  return (
    <div className="card why-card">
      <h3>Why does this scenario matter?</h3>
      <ul className="why-list">
        {points.map((point) => (
          <li key={point}>{point}</li>
        ))}
      </ul>
    </div>
  );
}

function complaintRowLabel(c: MigrationComplaint): string {
  const fromJur = c.current_jurisdiction_code ?? c.current_ward_code ?? "—";
  const toJur = c.proposed_jurisdiction_code ?? c.proposed_ward_code ?? "—";
  const fromSvc =
    (c.current_department_code ?? "") + (c.current_service_code ? ` / ${c.current_service_code}` : "");
  const toSvc =
    (c.proposed_department_code ?? "") + (c.proposed_service_code ? ` / ${c.proposed_service_code}` : "");
  return `${fromJur}${fromSvc ? ` (${fromSvc})` : ""} → ${toJur}${toSvc ? ` (${toSvc})` : ""}`;
}

function ImpactDetails({
  result,
  scenario,
  preview,
  previewLoading,
  previewError,
}: {
  result: WhatIfSimulateResponse;
  scenario: WhatIfScenarioSummary | null;
  preview: MigrationPreviewResponse | null;
  previewLoading: boolean;
  previewError: string | null;
}) {
  const affected = preview?.complaints.filter((c) => c.in_proposed_boundary) ?? [];
  const responsibilityChanged =
    preview?.complaints.filter((c) => c.responsibility_changed) ?? [];
  const migrated = preview?.complaints.filter((c) => c.migration_required) ?? [];
  const conflicts = conflictCount(result);
  const wardTransitions = new Set<string>();
  for (const c of migrated) {
    if (c.current_ward_code && c.proposed_ward_code) {
      wardTransitions.add(`${c.current_ward_code} → ${c.proposed_ward_code}`);
    }
  }

  return (
    <div className="impact-details">
      <details className="impact-detail" open>
        <summary>
          Affected complaints
          {preview ? <span className="count-chip">{preview.affected_count}</span> : <span className="count-chip">…</span>}
        </summary>
        {previewLoading && <p className="muted">Loading complaint preview…</p>}
        {previewError && <p className="error-text">{previewError}</p>}
        {preview && affected.length === 0 && (
          <p className="muted">
            No OPEN complaint falls inside the proposed boundary of {result.scenario_code} on the preview date.
          </p>
        )}
        {affected.length > 0 && (
          <div className="complaint-rows">
            {affected.map((c) => (
              <div key={c.public_ref} className="complaint-row">
                <code>{c.public_ref}</code>
                <em>{c.issue_type_name ?? c.issue_type}</em>
                <span className="muted">
                  ({c.latitude.toFixed(4)}, {c.longitude.toFixed(4)}) · ward {c.current_ward_code ?? "—"}
                </span>
                <span className="complaint-flip">{complaintRowLabel(c)}</span>
                {!c.responsibility_changed && (
                  <span className="complaint-badge">department/service unchanged</span>
                )}
                <p className="muted">{c.explanation}</p>
              </div>
            ))}
          </div>
        )}
      </details>

      <details className="impact-detail">
        <summary>
          Changed responsibilities
          <span className="count-chip">{result.responsibility_change_count}</span>
        </summary>
        {result.responsibility_deltas.length > 0 && (
          <>
            <h5 className="impact-subhead">
              Probe-point analysis{" "}
              <span className="muted">(this location, not complaint counts)</span>
            </h5>
            <div className="delta-rows">
            {result.responsibility_deltas.map((delta, index) => (
              <div key={index} className="delta-row">
                <div className="delta-current">
                  <h5>Current <span className="muted">(live)</span></h5>
                  <dl className="kv">
                    <div>
                      <dt>Ward</dt>
                      <dd>{result.current.ward_code ?? "—"} · {result.current.ward_name ?? ""}</dd>
                    </div>
                    <div>
                      <dt>Authority</dt>
                      <dd>{result.current.authority?.name ?? "—"}</dd>
                    </div>
                    <div>
                      <dt>Department</dt>
                      <dd>{result.current.department?.name ?? "—"}</dd>
                    </div>
                    <div>
                      <dt>Service</dt>
                      <dd>{result.current.service?.name ?? "—"}</dd>
                    </div>
                  </dl>
                </div>
                <div className="delta-arrow" aria-hidden="true">→</div>
                <div className="delta-proposed">
                  <h5>Proposed <span className="muted">(scenario)</span></h5>
                  <dl className="kv">
                    <div>
                      <dt>Scope</dt>
                      <dd>{delta.matched_scope ?? "changed"}</dd>
                    </div>
                    <div>
                      <dt>Authority</dt>
                      <dd>{delta.authority_name ?? delta.authority_code ?? "—"}</dd>
                    </div>
                    <div>
                      <dt>Department</dt>
                      <dd>{delta.department_name ?? delta.department_code ?? "—"}</dd>
                    </div>
                    <div>
                      <dt>Service</dt>
                      <dd>{delta.service_name ?? delta.service_code ?? "—"}</dd>
                    </div>
                  </dl>
                  <p className="muted">{delta.description}</p>
                </div>
              </div>
            ))}
            </div>
          </>
        )}
        {responsibilityChanged.length > 0 && (
          <div className="complaint-rows">
            <h5>
              Complaints switching department/service responsibility
              <span className="muted"> ({result.responsibility_change_count})</span>
            </h5>
            {responsibilityChanged.map((c) => (
              <div key={c.public_ref} className="complaint-row">
                <code>{c.public_ref}</code>
                <span className="complaint-flip">{complaintRowLabel(c)}</span>
              </div>
            ))}
          </div>
        )}
        {result.responsibility_deltas.length === 0 && responsibilityChanged.length === 0 && (
          <p className="muted">No responsibility mappings change for this simulation.</p>
        )}
      </details>

      <details className="impact-detail">
        <summary>
          Detected conflicts
          <span className="count-chip">{conflicts}</span>
        </summary>
        {conflicts > 0 ? (
          <>
            <ul className="conflict-list">
              {result.potential_conflicts
                .filter((c) => c && c !== "NONE")
                .map((c) => (
                  <li key={c}>
                    <code>{c}</code>
                  </li>
                ))}
            </ul>
            <p className="muted">
              The backend flagged the tag above for this probe under the proposed boundary.
            </p>
          </>
        ) : (
          <p className="muted">No responsibility conflicts detected.</p>
        )}
      </details>

      <details className="impact-detail">
        <summary>
          Affected geographic entities
          {result.affected_complaint_count > 0 ? <span className="count-chip">{scenario?.code ?? ""}</span> : null}
        </summary>
        <div className="geo-entity-grid">
          <dl className="kv">
            {scenario && (
              <>
                <div>
                  <dt>Scenario</dt>
                  <dd>
                    {scenario.code} · {scenario.name}
                  </dd>
                </div>
                {scenario.description && (
                  <div>
                    <dt>Description</dt>
                    <dd>{scenario.description}</dd>
                  </div>
                )}
                {scenario.affected_region_name && (
                  <div>
                    <dt>Affected region</dt>
                    <dd>{scenario.affected_region_name}</dd>
                  </div>
                )}
                <div>
                  <dt>Proposed geometry</dt>
                  <dd>{scenario.geometry_geojson ? "provided (overlay on map)" : "not stored"}</dd>
                </div>
                <div>
                  <dt>Status</dt>
                  <dd>{scenario.status}</dd>
                </div>
              </>
            )}
            <div>
              <dt>Current jurisdiction</dt>
              <dd>{result.current.jurisdiction_code ?? "—"}</dd>
            </div>
            <div>
              <dt>Proposed jurisdiction</dt>
              <dd>{result.proposed?.jurisdiction_code ?? "—"}</dd>
            </div>
            {wardTransitions.size > 0 && (
              <div>
                <dt>Ward transitions</dt>
                <dd>{[...wardTransitions].sort().join(", ")}</dd>
              </div>
            )}
          </dl>
        </div>
      </details>
    </div>
  );
}

function SimulationSafety({ scenario }: { scenario: WhatIfScenarioSummary | null }) {
  return (
    <div className="safety-note" role="status">
      <span className="safety-check" aria-hidden="true">
        ✓
      </span>
      <div>
        <strong>No active jurisdiction records were modified.</strong>
        <p className="muted">
          The simulator resolved against a strict read-only overlay — nothing was written to the
          live jurisdictions, versions, rules or complaints.
        </p>
        {scenario && (
          <p className="muted">
            Scenario <code>{scenario.code}</code> remains <strong>{scenario.status}</strong>; applying
            a scenario is a separate migration flow, not part of simulation.
          </p>
        )}
      </div>
    </div>
  );
}