import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../api";
import { simulateWhatIf, fetchWhatIfScenarios } from "../api/whatif";
import type { WhatIfSimulateResponse, WhatIfScenarioSummary } from "../api/whatifTypes";
import type { ImpactMetric } from "../api/whatifTypes";

const ON_DATE = "2026-09-18";

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
    point: { lon: 76.635, lat: 12.3125 },
    issue: "heritage_maintenance",
  },
  {
    label: "Flip point · V1/V2",
    code: "SC-V3-REZONE",
    point: { lon: 76.60731308845853, lat: 12.279255877741852 },
    issue: "garbage_collection",
  },
];

function metricDelta(metric: ImpactMetric): string {
  const delta = metric.proposed - metric.current;
  if (delta === 0) return "unchanged";
  return delta > 0 ? `+${delta}` : `${delta}`;
}

export default function WhatIfSimulatorPage() {
  const [state, setState] = useState<{ kind: "loading" } | { kind: "ok" } | { kind: "error"; message: string }>({ kind: "loading" });
  const [scenario, setScenario] = useState<WhatIfScenarioSummary | null>(null);
  const [lon, setLon] = useState("76.6438");
  const [lat, setLat] = useState("12.3082");
  const [issue, setIssue] = useState("heritage_maintenance");
  const [simulating, setSimulating] = useState(false);
  const [result, setResult] = useState<WhatIfSimulateResponse | null>(null);
  const [resultError, setResultError] = useState<string | null>(null);
  const [scenarios, setScenarios] = useState<WhatIfScenarioSummary[]>([]);

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

  const runSimulate = useCallback(
    (lng: number, latValue: number, issueType: string) => {
      setSimulating(true);
      setResultError(null);
      setResult(null);
      simulateWhatIf({
        longitude: lng,
        latitude: latValue,
        issue_type_code: issueType,
        on_date: ON_DATE,
      })
        .then((res) => setResult(res))
        .catch((error: unknown) =>
          setResultError(error instanceof ApiError ? error.message : "Unknown error"),
        )
        .finally(() => setSimulating(false));
    },
    [],
  );

  const handleQuick = (quick: QuickScenario) => {
    setLon(String(quick.point.lon));
    setLat(String(quick.point.lat));
    setIssue(quick.issue);
    runSimulate(quick.point.lon, quick.point.lat, quick.issue);
  };

  return (
    <section className="page">
      <header className="page-header">
        <h1>What-If Simulator</h1>
        <p>
          Run a proposed boundary against the live layout without touching a single row:
          the engine resolves responsibility today and under the scenario, then reports
          every delta — jurisdiction, ward, responsibility and complaint impact. Applying
          a scenario is an explicit, separate migration flow.
        </p>
        <div className="sim-only-badge">SIMULATION ONLY · NO LIVE JURISDICTION DATA MODIFIED</div>
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

        <div className="card gis-result-card">
          <h3>Simulation result</h3>
          {simulating && <p className="muted">Simulating responsibility…</p>}
          {resultError && <p className="error-text">{resultError}</p>}
          {!simulating && !resultError && !result && (
            <p className="muted">
              Pick a quick flip or enter a probe point to simulate a what-if.
            </p>
          )}
          {!simulating && !resultError && result && <SimulationResultView result={result} />}
        </div>
      </div>
    </section>
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

function SimulationResultView({ result }: { result: WhatIfSimulateResponse }) {
  return (
    <div className="whatif-result">
      <div className="whatif-head">
        <code className="whatif-scenario">{result.scenario_code}</code>
        <span className={`result-status ${result.in_proposed_geometry ? "ok-tag" : "muted-tag"}`}>
          {result.in_proposed_geometry ? "IN PROPOSED" : "OUTSIDE PROPOSAL"}
        </span>
      </div>

      <dl className="kv">
        <div>
          <dt>Scenario</dt>
          <dd>{result.scenario_name}</dd>
        </div>
        <div>
          <dt>On date</dt>
          <dd>{result.on_date}</dd>
        </div>
      </dl>

      <div className="ba-compare">
        <div className="card ba-card">
          <h4>
            Current boundary <span className="muted">(live)</span>
          </h4>
          <Strip label="Ward" code={result.current.ward_code} name={result.current.ward_name} status={result.current.status} />
          <Strip label="Authority" code={result.current.authority?.code ?? null} name={result.current.authority?.name ?? null} />
          <Strip label="Department" code={result.current.department?.code ?? null} name={result.current.department?.name ?? null} />
          <Strip label="Service" code={result.current.service?.code ?? null} name={result.current.service?.name ?? null} />
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
            <>
              <Strip label="Ward" code={result.proposed.ward_code} name={result.proposed.ward_name} status={result.proposed.status} />
              <Strip label="Authority" code={result.proposed.authority?.code ?? null} name={result.proposed.authority?.name ?? null} />
              <Strip label="Department" code={result.proposed.department?.code ?? null} name={result.proposed.department?.name ?? null} />
              <Strip label="Service" code={result.proposed.service?.code ?? null} name={result.proposed.service?.name ?? null} />
              <p className="muted">A change to the right is a migration candidate.</p>
            </>
          ) : (
            <p className="muted">No routing resolves under the proposed boundary.</p>
          )}
        </div>
      </div>

      {result.impact.length > 0 && (
        <div className="impact-block">
          <h4>Impact</h4>
          <table className="impact-table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>Current</th>
                <th>Proposed</th>
                <th>Delta</th>
              </tr>
            </thead>
            <tbody>
              {result.impact.map((metric) => (
                <tr key={metric.label}>
                  <td>{metric.label}</td>
                  <td>{metric.current}</td>
                  <td>{metric.proposed}</td>
                  <td>{metricDelta(metric)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted">
            {result.affected_complaint_count} complaint{result.affected_complaint_count === 1 ? "" : "s"} affected ·{" "}
            {result.responsibility_deltas.length} responsibility delta{result.responsibility_deltas.length === 1 ? "" : "s"}
          </p>
        </div>
      )}

      {result.potential_conflicts.length > 0 && (
        <div className="conflict-box">
          <h4>Potential conflicts</h4>
          <ul>
            {result.potential_conflicts.map((c) => (
              <li key={c}>
                <code>{c}</code>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
