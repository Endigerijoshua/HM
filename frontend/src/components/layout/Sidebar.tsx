import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/route", label: "Citizen Routing" },
  { to: "/history", label: "Historical Explorer" },
  { to: "/whatif", label: "What-If Simulator" },
  { to: "/migrations", label: "Complaint Migration" },
  { to: "/conflicts", label: "Responsibility Conflicts" },
  { to: "/graph", label: "Responsibility Graph" },
  { to: "/admin", label: "Admin Boundaries" },
];

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
        <span className="version-badge">v0.1.0 · HackMysuru 2026</span>
      </div>
    </aside>
  );
}