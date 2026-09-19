import { Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { ViewProvider, useViewMode } from "./components/layout/ViewContext";
import { ViewToggle } from "./components/layout/ViewToggle";
import AdminBoundaryPage from "./pages/AdminBoundaryPage";
import CitizenRoutingPage from "./pages/CitizenRoutingPage";
import ComplaintMigrationPage from "./pages/ComplaintMigrationPage";
import DashboardPage from "./pages/DashboardPage";
import HistoricalExplorerPage from "./pages/HistoricalExplorerPage";
import HistoricalReplayPage from "./pages/HistoricalReplayPage";
import ResponsibilityConflictsPage from "./pages/ResponsibilityConflictsPage";
import ResponsibilityGraphPage from "./pages/ResponsibilityGraphPage";
import WhatIfSimulatorPage from "./pages/WhatIfSimulatorPage";

function AppRoutes() {
  const { view } = useViewMode();

  if (view === "citizen") {
    return (
      <div className="app-shell app-view-citizen">
        <header className="citizen-bar">
          <div className="citizen-brand">
            <div className="brand-mark" />
            <div>
              <div className="brand-title">TCDT</div>
              <div className="brand-sub">Civic Jurisdiction Digital Twin</div>
            </div>
          </div>
          <ViewToggle />
        </header>
        <main className="citizen-content">
          <CitizenRoutingPage />
        </main>
      </div>
    );
  }

  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="route" element={<CitizenRoutingPage />} />
        <Route path="history" element={<HistoricalExplorerPage />} />
        <Route path="replay" element={<HistoricalReplayPage />} />
        <Route path="whatif" element={<WhatIfSimulatorPage />} />
        <Route path="migrations" element={<ComplaintMigrationPage />} />
        <Route path="conflicts" element={<ResponsibilityConflictsPage />} />
        <Route path="graph" element={<ResponsibilityGraphPage />} />
        <Route path="admin" element={<AdminBoundaryPage />} />
        <Route path="*" element={<MissingPage />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <ViewProvider>
      <AppRoutes />
    </ViewProvider>
  );
}

function MissingPage() {
  return (
    <section className="page">
      <h1>Page not found</h1>
      <p>This route does not exist in the demo application.</p>
    </section>
  );
}