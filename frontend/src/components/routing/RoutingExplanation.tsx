import type { ReactNode } from "react";
import type { RoutingResult } from "../../api/routingTypes";

interface RoutingExplanationProps {
  result: RoutingResult;
}

interface ExplainStep {
  icon: string;
  label: string;
  body: ReactNode;
}

function ExplainStepRow({ icon, label, body }: ExplainStep) {
  return (
    <li className="explain-node">
      <span className="explain-node-icon" aria-hidden="true">
        {icon}
      </span>
      <div className="explain-node-body">
        <span className="explain-node-label">{label}</span>
        <span className="explain-node-value">{body}</span>
      </div>
    </li>
  );
}

interface Check {
  label: string;
  detail: string;
  ok: boolean;
}

/**
 * "Why was this routed here?" panel. Pure presentation over the existing
 * routing response — nothing is recomputed or invented. Shows the full
 * explainable chain for RESOLVED results and an explicit warning that names
 * the step where resolution stopped otherwise.
 */
export function RoutingExplanation({ result }: RoutingExplanationProps) {
  if (result.status !== "RESOLVED") {
    const stoppedAt =
      result.status === "NO_JURISDICTION" || result.status === "INVALID_LOCATION"
        ? "Temporal Jurisdiction"
        : result.status === "TEMPORAL_CONFLICT" || result.status === "RESPONSIBILITY_UNRESOLVED"
          ? "Routing Rule"
          : result.status === "INVALID_ISSUE"
            ? "Issue"
            : result.status === "INVALID_DATE"
              ? "Date"
              : "Resolution";
    const stoppedReason =
      result.status === "RESPONSIBILITY_UNRESOLVED" || result.status === "TEMPORAL_CONFLICT"
        ? "Two or more equal-priority rules matched and disagree on ownership."
        : result.status === "NO_JURISDICTION" || result.status === "INVALID_LOCATION"
          ? "No jurisdiction covers this point on the requested date."
          : result.status === "INVALID_ISSUE"
            ? "The issue type is not registered in the decision table."
            : result.status === "INVALID_DATE"
              ? "The requested date is outside the supported routing window."
              : "The request could not be resolved.";

    return (
      <section className="explain-panel explain-panel-warn" aria-label="Why this route was not resolved">
        <header className="explain-head">
          <h3>Why was this routed here?</h3>
          <span className={`result-status ${STATUS_TONE[result.status]}`}>{result.status}</span>
        </header>
        <div className="explain-warn">
          <p className="explain-warn-step">
            Resolution stopped at <strong>{stoppedAt}</strong>.
          </p>
          <p>{stoppedReason}</p>
          {result.conflict_rule_codes.length > 0 && (
            <>
              <p className="muted">Conflicting rules matched:</p>
              <ul className="conflict-list">
                {result.conflict_rule_codes.map((code) => (
                  <li key={code}>
                    <code>{code}</code>
                  </li>
                ))}
              </ul>
            </>
          )}
          {result.reason && <p className="muted">{result.reason}</p>}
        </div>
        {result.explanation && <p className="why-route">{result.explanation}</p>}
        {(result.audit_id !== null || result.routing_rule_id !== null) && (
          <footer className="explain-audit">
            {result.audit_id !== null ? (
              <span>
                Decision / audit ID: <code>routing.resolve #{result.audit_id}</code>
              </span>
            ) : null}
            {result.routing_rule_id !== null ? (
              <span>
                Decision-table rule id: <code>#{result.routing_rule_id}</code>
              </span>
            ) : null}
          </footer>
        )}
      </section>
    );
  }

  const coords = `${result.longitude.toFixed(5)}, ${result.latitude.toFixed(5)}`;
  const jurisdictionValue = (
    <>
      <strong>{result.jurisdiction_code ?? "(none)"}</strong>
      {result.jurisdiction_name ? <span className="explain-node-detail"> · {result.jurisdiction_name}</span> : null}
      {result.jurisdiction_kind ? <span className="explain-node-detail"> · {result.jurisdiction_kind}</span> : null}
    </>
  );

  const wardValue = result.ward_code ? (
    <>
      <strong>{result.ward_code}</strong>
      {result.ward_name ? <span className="explain-node-detail"> · {result.ward_name}</span> : null}
    </>
  ) : (
    <>
      <strong>{result.matched_scope ?? result.jurisdiction_kind ?? "Area"}</strong>
    </>
  );

  const escalationValue = result.escalation_path.length
    ? result.escalation_path.map((step) => step.authority.name).join(" → ")
    : "—";

  const checks: Check[] = [
    { label: "Valid coordinates", detail: `${result.latitude.toFixed(4)}, ${result.longitude.toFixed(4)}`, ok: true },
    { label: "Jurisdiction found for requested date", detail: result.version_code ?? "CURRENT", ok: Boolean(result.jurisdiction_code) },
    { label: "Issue type matched", detail: result.issue_type, ok: Boolean(result.routing_rule_code) },
    { label: "Responsibility rule matched", detail: result.routing_rule_code ?? "—", ok: Boolean(result.routing_rule_code) },
    { label: "Service resolved", detail: result.service?.code ?? "—", ok: Boolean(result.service) },
  ];

  const steps: ExplainStep[] = [
    {
      icon: "📍",
      label: "Location",
      body: (
        <>
          Coordinates: <code>{coords}</code>
          <span className="explain-node-detail"> · {result.issue_type} · {result.effective_date}</span>
        </>
      ),
    },
    {
      icon: "🗺",
      label: "Temporal Jurisdiction",
      body: (
        <>
          {jurisdictionValue}
          <span className="explain-node-detail">
            {" "}
            · Version: {result.version_code ?? "(none)"}
            {result.version_status ? ` (${result.version_status})` : ""}
          </span>
        </>
      ),
    },
    {
      icon: "🗂",
      label: "Ward / Area",
      body: (
        <>
          {wardValue}
          {result.matched_scope ? <span className="explain-node-detail"> · matched scope: {result.matched_scope}</span> : null}
        </>
      ),
    },
    {
      icon: "🏛",
      label: "Responsible Authority",
      body: (
        <>
          <strong>{result.authority?.code ?? "(none)"}</strong>
          {result.authority?.name ? <span className="explain-node-detail"> · {result.authority.name}</span> : null}
        </>
      ),
    },
    {
      icon: "🏢",
      label: "Department",
      body: (
        <>
          <strong>{result.department?.code ?? "(none)"}</strong>
          {result.department?.name ? <span className="explain-node-detail"> · {result.department.name}</span> : null}
        </>
      ),
    },
    {
      icon: "🛠",
      label: "Service",
      body: (
        <>
          <strong>{result.service?.code ?? "(none)"}</strong>
          {result.service?.name ? <span className="explain-node-detail"> · {result.service.name}</span> : null}
          {result.sla_days !== null ? <span className="explain-node-detail"> · SLA {result.sla_days} days</span> : null}
        </>
      ),
    },
    {
      icon: "📋",
      label: "Routing Rule",
      body: (
        <>
          <code>{result.routing_rule_code ?? "(none)"}</code>
          <span className="explain-node-detail"> · rule id #{result.routing_rule_id ?? "—"}</span>
        </>
      ),
    },
    {
      icon: "🚨",
      label: "Escalation Path",
      body: (
        <>
          {escalationValue}
          {result.escalation_path.length > 0 && (
            <span className="explain-node-detail">
              {" "}
              · steps: {result.escalation_path.map((step) => `#${step.step_number} ${step.authority.code}${step.note ? ` (${step.note})` : ""}`).join(", ")}
            </span>
          )}
        </>
      ),
    },
  ];

  return (
    <section className="explain-panel" aria-label="Why this route was chosen">
      <header className="explain-head">
        <h3>Why was this routed here?</h3>
        <span className={`result-status ${STATUS_TONE[result.status]}`}>{result.status}</span>
      </header>

      <div className="explain-checks" aria-label="Decision basis">
        {checks.map((check) => (
          <span key={check.label} className={`check-item ${check.ok ? "check-ok" : "check-no"}`}>
            <span aria-hidden="true">{check.ok ? "✓" : "✗"}</span>
            <span className="check-label">{check.label}</span>
            <code className="check-detail">{check.detail}</code>
          </span>
        ))}
      </div>

      <ol className="explain-chain">
        {steps.map((step, index) => (
          <li key={step.label} className="explain-step-wrap">
            <ExplainStepRow {...step} />
            {index < steps.length - 1 && (
              <span className="explain-arrow" aria-hidden="true">
                ↓
              </span>
            )}
          </li>
        ))}
      </ol>

      <footer className="explain-audit">
        <span>
          Decision / audit ID: <code>{result.audit_id !== null ? `routing.resolve #${result.audit_id}` : "—"}</code>
        </span>
        <span className="explain-map-link">
          Map: probe marker and <strong>{result.jurisdiction_code ?? "jurisdiction"}</strong> boundary highlight use
          exactly these coordinates.
        </span>
      </footer>
    </section>
  );
}

const STATUS_TONE: Record<string, string> = {
  RESOLVED: "ok-tag",
  RESPONSIBILITY_UNRESOLVED: "bad-tag",
  NO_JURISDICTION: "muted-tag",
  TEMPORAL_CONFLICT: "warn-tag",
  INVALID_LOCATION: "bad-tag",
  INVALID_ISSUE: "bad-tag",
  INVALID_DATE: "bad-tag",
};