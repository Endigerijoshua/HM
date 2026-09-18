import { Link } from "react-router-dom";

const STEPS = [
  { key: "route", label: "Routing", to: "/route?demo=1" },
  { key: "replay", label: "Historical Replay", to: "/replay" },
  { key: "whatif", label: "What-If Simulator", to: "/whatif" },
  { key: "migrations", label: "Complaint Migration", to: "/migrations" },
  { key: "conflicts", label: "Conflicts", to: "/conflicts" },
  { key: "graph", label: "Responsibility Graph", to: "/graph" },
];

export function DemoFlowBar({ active }: { active: string }) {
  return (
    <nav className="demo-flow" aria-label="Demo flow">
      <span className="demo-flow-badge">DEMO MODE</span>
      <span className="demo-flow-intro">Follow the flow:</span>
      <div className="demo-flow-links">
        {STEPS.map((step, index) => (
          <span key={step.key} className="demo-flow-step">
            <Link
              to={step.to}
              className={`demo-flow-link${active === step.key ? " active" : ""}`}
              aria-current={active === step.key ? "page" : undefined}
            >
              {step.label}
            </Link>
            {index < STEPS.length - 1 && (
              <span className="demo-flow-arrow" aria-hidden="true">→</span>
            )}
          </span>
        ))}
      </div>
    </nav>
  );
}