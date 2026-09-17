import { Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import AdminBoundaryPage from "./pages/AdminBoundaryPage";
import CitizenRoutingPage from "./pages/CitizenRoutingPage";
import ComplaintMigrationPage from "./pages/ComplaintMigrationPage";
import DashboardPage from "./pages/DashboardPage";
import HistoricalExplorerPage from "./pages/HistoricalExplorerPage";
import ResponsibilityConflictsPage from "./pages/ResponsibilityConflictsPage";
import ResponsibilityGraphPage from "./pages/ResponsibilityGraphPage";
import WhatIfSimulatorPage from "./pages/WhatIfSimulatorPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="route" element={<CitizenRoutingPage />} />
        <Route path="history" element={<HistoricalExplorerPage />} />
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

function MissingPage() {
  return (
    <section className="page">
      <h1>Page not found</h1>
      <p>This route does not exist in the demo application.</p>
    </section>
  );
}