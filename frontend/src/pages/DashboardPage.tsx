import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { ApiHealth } from "../api";
import { ApiError, fetchHealth } from "../api";

const MODULES = [
  { name: "P1 · GIS / Temporal Jurisdiction", to: "/history", phase: "P1", status: "IMPLEMENTED" },
  { name: "P2 · Citizen Routing", to: "/route", phase: "P2", status: "IMPLEMENTED" },
  { name: "P3 · What-If Simulator", to: "/whatif", phase: "P3", status: "IMPLEMENTED" },
  { name: "P4 · Complaint Migration Preview", to: "/migrations", phase: "P4", status: "IMPLEMENTED" },
  { name: "P5 · Responsibility Conflicts", to: "/conflicts", phase: "P5", status: "IMPLEMENTED" },
  { name: "P6 · Responsibility Graph", to: "/graph", phase: "P6", status: "IMPLEMENTED" },
  { name: "P7 · Historical Replay", to: "/replay", phase: "P7", status: "IMPLEMENTED" },
];

const PIPELINE = [
  { label: "LOCATION", hint: "lat, lng" },
  { label: "JURISDICTION", hint: "versioned boundary" },
  { label: "AUTHORITY", hint: "who owns it" },
  { label: "DEPARTMENT", hint: "who runs it" },
  { label: "SERVICE", hint: "the SLA" },
  { label: "ESCALATION", hint: "what happens next" },
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
          One deterministic explainable pipeline decides who is responsible for
          an issue at a location on a date — jurisdiction versions and routing
          rules change over time, and this twin replays, simulates and previews
          every consequence.
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
          <h3>Core concept</h3>
          <div className="concept-formula">
            Responsible Entity =
            <br />
            <span className="concept-term">Location</span> +{" "}
            <span className="concept-term">Issue</span> +{" "}
            <span className="concept-term">Date</span>
            <br />
            + <span className="concept-term">Jurisdiction Version</span> +{" "}
            <span className="concept-term">Rules</span>
          </div>
          <p className="muted">
            Change the date or the boundary version and the same coordinate can
            be someone else's responsibility — the Historical Replay page makes
            that transition explicit.
          </p>
          <Link to="/route" className="btn btn-primary">
            Start Demo → Citizen Routing
          </Link>
        </div>
      </div>

      <h2 className="section-title">Responsibility pipeline</h2>
      <div className="pipeline">
        {PIPELINE.map((step, index) => (
          <div key={step.label} className="pipeline-step">
            <div className={`resp-graph-node resp-graph-node-${step.label.toLowerCase()}`}>
              <span className="resp-graph-node-type">{step.label}</span>
              <span className="resp-graph-node-label">{step.hint}</span>
            </div>
            {index < PIPELINE.length - 1 && (
              <div className="pipeline-arrow" aria-hidden="true">
                ↓
              </div>
            )}
          </div>
        ))}
      </div>

      <h2 className="section-title">Implemented modules</h2>
      <div className="card-grid">
        {MODULES.map((module) => (
          <Link key={module.name} to={module.to} className="card small module-card">
            <div className="module-head">
              <span className="module-name">{module.name}</span>
              <span className="implemented-badge">{module.status}</span>
            </div>
            <span className="muted">Phase {module.phase} · live backend</span>
          </Link>
        ))}
      </div>
    </section>
  );
}