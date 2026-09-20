import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { ApiHealth } from "../api";
import { ApiError, API_BASE, fetchHealth } from "../api";

const DEMO_ROUTE = "/route?demo=1&lat=12.3082&lng=76.6438&issue=pothole&date=2024-06-01";

const MODULES = [
  { name: "P1 · GIS / Temporal Jurisdiction", to: "/history", phase: "P1", status: "IMPLEMENTED" },
  { name: "P2 · Citizen Routing", to: "/route", phase: "P2", status: "IMPLEMENTED" },
  { name: "P3 · What-If Simulator", to: "/whatif", phase: "P3", status: "IMPLEMENTED" },
  { name: "P4 · Complaint Migration Preview", to: "/migrations", phase: "P4", status: "IMPLEMENTED" },
  { name: "P5 · Responsibility Conflicts", to: "/conflicts", phase: "P5", status: "IMPLEMENTED" },
  { name: "P6 · Responsibility Graph", to: "/graph", phase: "P6", status: "IMPLEMENTED" },
  { name: "P7 · Historical Replay", to: "/replay", phase: "P7", status: "IMPLEMENTED" },
  { name: "P8 · Admin Boundaries (read-only)", to: "/admin", phase: "P8", status: "IMPLEMENTED" },
];

const WORKFLOW_ROUTING = [
  { label: "Location + Issue + Date", hint: "lat, lng, on_date", tone: "location" },
  { label: "Jurisdiction", hint: "versioned boundary", tone: "jurisdiction" },
  { label: "Authority", hint: "who owns it", tone: "authority" },
  { label: "Department", hint: "who runs it", tone: "department" },
  { label: "Service", hint: "the SLA that acts", tone: "service" },
  { label: "Routing Rule", hint: "deterministic match", tone: "rule" },
  { label: "Escalation", hint: "if unresolved", tone: "escalation" },
];

const WORKFLOW_IMPACT = [
  { label: "Boundary Change", hint: "version superseded", tone: "boundary-change" },
  { label: "What-If Simulation", hint: "proposed geometry", tone: "what-if" },
  { label: "Affected Complaints", hint: "migration preview", tone: "affected-complaints" },
  { label: "Responsibility Conflicts", hint: "conflicting rules", tone: "responsibility-conflicts" },
  { label: "Historical Replay", hint: "re-resolve over time", tone: "historical-replay" },
];

type HealthState =
  | { kind: "loading" }
  | { kind: "ok"; health: ApiHealth }
  | { kind: "error"; message: string };

function Pipeline({ steps }: { steps: { label: string; hint: string; tone: string }[] }) {
  return (
    <div className="pipeline">
      {steps.map((step, index) => (
        <div key={step.label} className="pipeline-step">
          <div className={`resp-graph-node resp-graph-node-${step.tone}`}>
            <span className="resp-graph-node-type">{step.label}</span>
            <span className="resp-graph-node-label">{step.hint}</span>
          </div>
          {index < steps.length - 1 && (
            <div className="pipeline-arrow" aria-hidden="true">
              ↓
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

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

  const networkDown = state.kind === "error" && state.message.startsWith("Backend is unreachable");

  return (
    <section className="page">
      <header className="page-header dashboard-hero">
        <h1 className="hero-title">JanSetu · Temporal Civic Jurisdiction Digital Twin</h1>
        <p className="hero-subtitle">
          Determine who is responsible for a civic issue when jurisdiction boundaries change
          over time.
        </p>
        <div className="hero-actions">
          <Link to={DEMO_ROUTE} className="btn btn-primary btn-lg">
            START DEMO ↗
          </Link>
          <Link to="/whatif" className="btn btn-outline btn-lg">
            Explore What-If →
          </Link>
        </div>
      </header>

      <div className="card-grid">
        <div className="card">
          <h3>Backend connection</h3>
          {state.kind === "loading" && <p className="muted">Checking connection…</p>}
          {state.kind === "error" && (
            <>
              <p className="error-text">
                {networkDown
                  ? "Backend unavailable. Start the FastAPI server on the configured development port."
                  : "Backend reported an error."}
              </p>
              <p className="muted">
                {networkDown ? `Waiting for API at ${API_BASE}` : state.message}
              </p>
            </>
          )}
          {state.kind === "ok" && (
            <>
              <dl className="kv">
                <div><dt>Status</dt><dd className={state.health.status === "ok" ? "ok-tag" : ""}>{state.health.status}</dd></div>
                <div><dt>Database</dt><dd>{state.health.database_status}</dd></div>
                <div><dt>Demo seed</dt><dd>{state.health.seed_loaded ? "Loaded" : "Empty"}</dd></div>
                <div><dt>Geometry engine</dt><dd>{state.health.geometry_engine}</dd></div>
                <div><dt>App version</dt><dd>{state.health.app_version}</dd></div>
              </dl>
              <p className="muted">Backend: <code>{API_BASE}</code></p>
            </>
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
            Change the date or the boundary version and the same coordinate can be someone
            else's responsibility. The twin replays, simulates and previews every consequence
            before any live record is touched.
          </p>
          <Link to={DEMO_ROUTE} className="btn btn-primary">
            Start Demo → Citizen Routing
          </Link>
        </div>
      </div>

      <h2 className="section-title">Routing pipeline</h2>
      <p className="muted workflow-note">
        A single deterministic, explainable path from a civic issue to the accountable entity.
      </p>
      <div className="workflow-card">
        <Pipeline steps={WORKFLOW_ROUTING} />
      </div>

      <h2 className="section-title">Impact planning</h2>
      <p className="muted workflow-note">
        What happens when boundaries change — modelled before it happens, never applied live.
      </p>
      <div className="workflow-card">
        <Pipeline steps={WORKFLOW_IMPACT} />
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