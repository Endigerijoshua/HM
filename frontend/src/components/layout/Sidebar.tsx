import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { fetchHealth } from "../../api";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/route", label: "Citizen Routing" },
  { to: "/history", label: "Historical Explorer" },
  { to: "/replay", label: "Historical Replay" },
  { to: "/whatif", label: "What-If Simulator" },
  { to: "/migrations", label: "Complaint Migration" },
  { to: "/conflicts", label: "Responsibility Conflicts" },
  { to: "/graph", label: "Responsibility Graph" },
];

type BackendState =
  | { kind: "checking" }
  | { kind: "up" }
  | { kind: "down" };

function BackendDot() {
  const [state, setState] = useState<BackendState>({ kind: "checking" });

  useEffect(() => {
    let cancelled = false;
    fetchHealth()
      .then(() => {
        if (!cancelled) setState({ kind: "up" });
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({
            kind: "down",
          });
          void error;
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const title =
    state.kind === "up"
      ? "Backend connected"
      : state.kind === "down"
        ? "Backend unreachable"
        : "Checking backend…";

  return <span className={`backend-dot backend-dot-${state.kind}`} title={title} aria-label={title} />;
}

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark" />
        <div>
          <div className="brand-title">TCDT</div>
          <div className="brand-sub">Civic Jurisdiction Twin</div>
        </div>
      </div>

      <nav className="nav">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <span className="version-badge">
          <BackendDot /> v0.1.0 · HackMysuru 2026
        </span>
      </div>
    </aside>
  );
}