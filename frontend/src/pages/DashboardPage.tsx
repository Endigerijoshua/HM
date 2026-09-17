import { useEffect, useState } from "react";
import type { ApiHealth } from "../api";
import { ApiError, fetchHealth } from "../api";

const MODULES = [
  { name: "Citizen Routing", phase: "P1", status: "Planned" },
  { name: "Historical Explorer", phase: "P1", status: "Planned" },
  { name: "What-If Simulator", phase: "P2", status: "Planned" },
  { name: "Complaint Migration", phase: "P2", status: "Planned" },
  { name: "Responsibility Conflicts", phase: "P3", status: "Planned" },
  { name: "Responsibility Graph", phase: "P3", status: "Planned" },
  { name: "Admin Boundary Management", phase: "P1-P3", status: "Planned" },
];

type HealthState =
  | { kind: "loading" }
  | { kind: "ok"; health: ApiHealth }
  | { kind: "error"; message: string };

export default function DashboardPage() {
  const [state, setState] = useState<HealthState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    fetchHealth()
      .then((health) => {
        if (!cancelled) setState({ kind: "ok", health });
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

  return (
    <section className="page">
      <header className="page-header">
        <h1>Dashboard</h1>
        <p>
          Deterministic, explainable civic routing across versioned jurisdiction
          boundaries that change over time.
        </p>
      </header>

      <div className="card-grid">
        <div className="card">
          <h3>Backend connection</h3>
          {state.kind === "loading" && <p className="muted">Checking health…</p>}
          {state.kind === "error" && (
            <>
              <p className="error-text">Backend unreachable</p>
              <p className="muted">{state.message}</p>
            </>
          )}
          {state.kind === "ok" && (
            <dl className="kv">
              <div><dt>Status</dt><dd className={state.health.status === "ok" ? "ok-tag" : ""}>{state.health.status}</dd></div>
              <div><dt>Database</dt><dd>{state.health.database_status}</dd></div>
              <div><dt>Demo seed</dt><dd>{state.health.seed_loaded ? "Loaded" : "Empty"}</dd></div>
              <div><dt>Geometry engine</dt><dd>{state.health.geometry_engine}</dd></div>
              <div><dt>App version</dt><dd>{state.health.app_version}</dd></div>
            </dl>
          )}
        </div>

        <div className="card">
          <h3>Core idea</h3>
          <p>
            Responsible entity = f(lat, lng, issue, date, boundary version, rules).
          </p>
          <p>
            P0 provides the temporal, versioned data foundation and the
            GIS abstraction. Routing, what-if and migration engines arrive in
            later phases.
          </p>
        </div>
      </div>

      <h2 className="section-title">Module roadmap</h2>
      <div className="card-grid">
        {MODULES.map((module) => (
          <div key={module.name} className="card small">
            <div className="module-head">
              <span className="module-name">{module.name}</span>
              <span className="phase">{module.status}</span>
            </div>
            <span className="muted">Target phase {module.phase}</span>
          </div>
        ))}
      </div>
    </section>
  );
}