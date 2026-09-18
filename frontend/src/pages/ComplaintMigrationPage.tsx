import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../api";
import { fetchMigrationPreview } from "../api/migrations";
import type { MigrationComplaint, MigrationPreviewResponse } from "../api/migrationTypes";
import { fetchWhatIfScenarios } from "../api/whatif";
import type { WhatIfScenarioSummary } from "../api/whatifTypes";

type LoadState =
  | { kind: "loading" }
  | { kind: "ok"; preview: MigrationPreviewResponse }
  | { kind: "error"; message: string };

function cell(code: string | null, name: string | null) {
  return { code: code ?? null, name: name ?? null };
}

function MigrateRow({ complaint }: { complaint: MigrationComplaint }) {
  const currentJurisdiction = cell(complaint.current_jurisdiction_code, complaint.current_jurisdiction_name);
  const proposedJurisdiction = cell(complaint.proposed_jurisdiction_code, complaint.proposed_jurisdiction_name);
  const migrated = complaint.migration_required;
  const inProposed = complaint.in_proposed_boundary;

  return (
    <tr className={migrated ? "migrate-row-detected" : ""}>
      <td>
        <code>{complaint.public_ref}</code>
        {!migrated && inProposed && <span className="muted"> · already aligned</span>}
      </td>
      <td>{complaint.issue_type}</td>
      <td className="old-cell">
        <div className="mini-stack">
          <span>{currentJurisdiction.code ?? "(none)"}</span>
          <span>{complaint.current_authority_code ?? "—"}</span>
          <span>{complaint.current_department_code ?? "—"}</span>
          <span>{complaint.current_service_code ?? "—"}</span>
        </div>
      </td>
      <td className="arrow-cell" aria-hidden="true">
        <span className="migration-arrow">→</span>
      </td>
      <td className="new-cell">
        <div className="mini-stack">
          <span>{proposedJurisdiction.code ?? "(none)"}</span>
          <span>{complaint.proposed_authority_code ?? "—"}</span>
          <span>{complaint.proposed_department_code ?? "—"}</span>
          <span>{complaint.proposed_service_code ?? "—"}</span>
        </div>
      </td>
      <td>
        {migrated ? (
          <span className="implied-badge">MIGRATION REQUIRED</span>
        ) : (
          <span className="phase">NO CHANGE</span>
        )}
      </td>
    </tr>
  );
}

export default function ComplaintMigrationPage() {
  const [scenarios, setScenarios] = useState<WhatIfScenarioSummary[]>([]);
  const [scenarioCode, setScenarioCode] = useState("");
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    fetchWhatIfScenarios()
      .then((response) => {
        if (cancelled) return;
        setScenarios(response.scenarios);
        setScenarioCode(response.scenarios[0]?.code ?? "");
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({ kind: "error", message: error instanceof ApiError ? error.message : "Unknown error" });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const loadPreview = useCallback((code: string) => {
    if (!code) return;
    setState({ kind: "loading" });
    fetchMigrationPreview(code)
      .then((preview) => setState({ kind: "ok", preview }))
      .catch((error: unknown) =>
        setState({ kind: "error", message: error instanceof ApiError ? error.message : "Unknown error" }),
      );
  }, []);

  useEffect(() => {
    if (scenarioCode) loadPreview(scenarioCode);
  }, [scenarioCode, loadPreview]);

  const preview = state.kind === "ok" ? state.preview : null;

  return (
    <section className="page">
      <header className="page-header">
        <h1>Complaint Migration </h1>
        <p>
          Preview which OPEN complaints change responsibility if a proposed
          scenario boundary becomes live — authority, department and service
          before and after. Preview only: nothing is applied.
        </p>
        <div className="sim-only-badge">READ-ONLY PREVIEW · NO MIGRATION APPLIED</div>
      </header>

      <div className="gis-toolbar">
        <div className="gis-toolbar-item">
          <label htmlFor="migration-scenario">Scenario</label>
          <select
            id="migration-scenario"
            value={scenarioCode}
            onChange={(event) => setScenarioCode(event.target.value)}
          >
            {scenarios.map((s) => (
              <option key={s.code} value={s.code}>
                {s.code} · {s.name}
              </option>
            ))}
          </select>
        </div>
        {preview && (
          <span className="gis-count">
            Affected complaints: <strong>{preview.affected_count}</strong> of{" "}
            {preview.total_open_complaints} open · preview date {preview.preview_date}
          </span>
        )}
      </div>

      {state.kind === "loading" && <p className="muted">Loading migration preview…</p>}
      {state.kind === "error" && <p className="error-text">{state.message}</p>}
      {!preview && state.kind !== "loading" && state.kind !== "error" && (
        <p className="muted">Select a scenario to preview migrations.</p>
      )}

      {preview && (
        <div className="card">
          <div className="module-head">
            <h3>
              {preview.scenario_name} · {preview.affected_count} complaint
              {preview.affected_count === 1 ? "" : "s"} affected
            </h3>
            <span className="phase">{preview.scenario_code}</span>
          </div>

          {preview.complaints.length === 0 ? (
            <p className="muted">No open complaints are affected by this scenario.</p>
          ) : (
            <div className="table-scroll">
              <table className="migration-table">
                <thead>
                  <tr>
                    <th>Complaint</th>
                    <th>Issue</th>
                    <th>Current (jurisdiction / authority / department / service)</th>
                    <th>
                      <span className="migration-arrow">OLD → NEW</span>
                    </th>
                    <th>Proposed (jurisdiction / authority / department / service)</th>
                    <th>Migration required</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.complaints.map((c) => (
                    <MigrateRow key={c.complaint_id} complaint={c} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  );
}