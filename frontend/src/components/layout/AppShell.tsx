import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";

export function AppShell() {
  const [navOpen, setNavOpen] = useState(false);

  useEffect(() => {
    document.body.style.overflow = navOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [navOpen]);

  return (
    <div className={`app-shell${navOpen ? " nav-open" : ""}`}>
      <Sidebar onNavigate={() => setNavOpen(false)} />
      <main className="content">
        <button
          type="button"
          className="nav-toggle"
          aria-expanded={navOpen}
          aria-controls="sidebar-nav"
          aria-label={navOpen ? "Close navigation menu" : "Open navigation menu"}
          onClick={() => setNavOpen((open) => !open)}
        >
          <span className="nav-toggle-icon" aria-hidden="true">
            ☰
          </span>
          Menu
        </button>
        <div
          className={`nav-backdrop${navOpen ? " is-visible" : ""}`}
          aria-hidden="true"
          onClick={() => setNavOpen(false)}
        />
        <Outlet />
      </main>
    </div>
  );
}