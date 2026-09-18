import { useEffect, useMemo, useState } from "react";
import { ApiError, fetchConflicts } from "../api";
import type { ResponsibilityConflict } from "../api/conflictsTypes";

type LoadState =
  | { kind: "loading" }
  | { kind: "ok"; conflicts: ResponsibilityConflict[] }
  | { kind: "error"; message: string };

function actorLabel(actor: { code: string; name: string } | null): string {
  return actor ? `${actor.code}` : "(none)";
}

export default function ResponsibilityConflictsPage() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    fetchConflicts()
      .then((response) => {
        if (!cancelled) setState({ kind: "ok", conflicts: response.conflicts });
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

  const summaries = useMemo(() => {
    const conflicts = state.kind === "ok" ? state.conflicts : [];
    const byType = new Map<string, number>();
    const bySeverity = new Map<string, number>();
    const byStatus = new Map<string, number>();
    for (const c of conflicts) {
      byType.set(c.conflict_type, (byType.get(c.conflict_type) ?? 0) + 1);
      byStatus.set(c.status, (byStatus.get(c.status) ?? 0) + 1);
      const severity = c.severity ?? "UNSPECIFIED";
      bySeverity.set(severity, (bySeverity.get(severity) ?? 0) + 1);
    }
    return { byType, bySeverity, byStatus };
  }, [state]);

  const conflicts = state.kind === "ok" ? state.conflicts : [];

  return (
    <section className="page">
      <header className="page-header">
        <h1>Responsibility Conflicts</h1>
        <p>
          Deterministic disagreements between the jurisdiction geography
          (expected responsibility) and the routing decision table (routed
          responsibility) — including temporal-rule conflicts and gaps where no
          responsibility can be established.
        </p>
      </header>

      {state.kind === "loading" && <p className="muted">Loading conflicts…</p>}
      {state.kind === "error" && <p className="error-text">{state.message}</p>}

      {state.kind === "ok" && conflicts.length === 0 && (
        <div className="card">
          <p className="muted">No responsibility conflicts detected.</p>
        </div>
      )}

      {state.kind === "ok" && conflicts.length > 0 && (
        <>
          <div className="summary-chips">
            <span className="summary-chip">Total {conflicts.length}</span>
            {["AUTHORITY_MISMATCH", "DEPARTMENT_MISMATCH", "SERVICE_MISMATCH", "TEMPORAL_RULE_CONFLICT", "RESPONSIBILITY_GAP"].map(
              (type) =>
                (summaries.byType.get(type) ?? 0) > 0 && (
                  <span key={type} className="summary-chip">
                    {type.split("_").join(" ")}: {summaries.byType.get(type)}
                  </span>
                ),
            )}
          </div>

          <div className="summary-chips">
            {Array.from(summaries.bySeverity.entries()).map(([severity, count]) => (
              <span key={severity} className="summary-chip">
                {severity}: {count}
              </span>
            ))}
            {Array.from(summaries.byStatus.entries()).map(([status, count]) => (
              <span key={status} className="summary-chip">
                {status}: {count}
              </span>
            ))}
          </div>

          <div className="card">
            <div className="table-scroll">
              <table className="conflicts-table">
                <thead>
                  <tr>
                    <th>Complaint</th>
                    <th>Issue</th>
                    <th>Jurisdiction</th>
                    <th>Conflict type</th>
                    <th>Severity</th>
                    <th>Expected → Routed</th>
                    <th>Status</th>
                    <th>Explanation</th>
                  </tr>
                </thead>
                <tbody>
                  {conflicts.map((c) => (
                    <tr key={c.conflict_id}>
                      <td>
                        <code>{c.complaint_ref ?? "—"}</code>
                        <br />
                        <span className="muted">
                          {c.latitude.toFixed(4)}, {c.longitude.toFixed(4)}
                        </span>
                      </td>
                      <td>
                        {c.issue_type ?? "—"}
                        {c.date ? <div className="muted">{c.date}</div> : null}
                      </td>
                      <td>
                        <code>{c.jurisdiction_code ?? "—"}</code>
                        <div className="muted">{c.jurisdiction_name ?? ""}</div>
                      </td>
                      <td>
                        <code>{c.conflict_type}</code>
                      </td>
                      <td>
                        <span className={`result-status ${c.severity === "HIGH" ? "bad-tag" : "warn-tag"}`}>
                          {c.severity ?? "—"}
                        </span>
                      </td>
                      <td>
                        <div className="mini-stack">
                          <span>
                            A {actorLabel(c.expected_authority)} → {actorLabel(c.routed_authority)}
                          </span>
                          <span>
                            D {actorLabel(c.expected_department)} → {actorLabel(c.routed_department)}
                          </span>
                          <span>
                            S {actorLabel(c.expected_service)} → {actorLabel(c.routed_service)}
                          </span>
                        </div>
                      </td>
                      <td>
                        <span className="phase">{c.status}</span>
                      </td>
                      <td className="explanation-cell">{c.explanation}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </section>
  );
}