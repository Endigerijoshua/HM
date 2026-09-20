import type { ReactNode } from "react";
import type { RoutingResult, RoutingStatus } from "../../api/routingTypes";
import { fill, type Dict } from "../../lib/i18n/citizenStrings";

interface RoutingExplanationProps {
  result: RoutingResult;
  dict: Dict;
}

interface ExplainStep {
  icon: string;
  label: string;
  body: ReactNode;
}

interface Check {
  label: string;
  detail: string;
  ok: boolean;
}

const STATUS_TONE: Record<RoutingStatus, string> = {
  RESOLVED: "ok-tag",
  RESPONSIBILITY_UNRESOLVED: "bad-tag",
  NO_JURISDICTION: "muted-tag",
  TEMPORAL_CONFLICT: "warn-tag",
  INVALID_LOCATION: "bad-tag",
  INVALID_ISSUE: "bad-tag",
  INVALID_DATE: "bad-tag",
};

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

/**
 * "Why was this routed here?" panel. Pure presentation over the existing
 * routing response — nothing is recomputed or invented. Shows the full
 * explainable chain for RESOLVED results and an explicit warning that names
 * the step where resolution stopped otherwise.
 */
export function RoutingExplanation({ result, dict }: RoutingExplanationProps) {
  if (result.status !== "RESOLVED") {
    const stopKey: "jurisdiction" | "rule" | "issue" | "date" | "resolution" =
      result.status === "NO_JURISDICTION" || result.status === "INVALID_LOCATION"
        ? "jurisdiction"
        : result.status === "TEMPORAL_CONFLICT" || result.status === "RESPONSIBILITY_UNRESOLVED"
          ? "rule"
          : result.status === "INVALID_ISSUE"
            ? "issue"
            : result.status === "INVALID_DATE"
              ? "date"
              : "resolution";
    const stopReasonKey: "tie" | "noJurisdiction" | "unknownIssue" | "invalidDate" | "fallback" =
      result.status === "RESPONSIBILITY_UNRESOLVED" || result.status === "TEMPORAL_CONFLICT"
        ? "tie"
        : result.status === "NO_JURISDICTION" || result.status === "INVALID_LOCATION"
          ? "noJurisdiction"
          : result.status === "INVALID_ISSUE"
            ? "unknownIssue"
            : result.status === "INVALID_DATE"
              ? "invalidDate"
              : "fallback";

    return (
      <section className="explain-panel explain-panel-warn" aria-label={dict.explainAriaNotResolved}>
        <header className="explain-head">
          <h3>{dict.explainTitle}</h3>
          <span className={`result-status ${STATUS_TONE[result.status]}`}>{result.status}</span>
        </header>
        <div className="explain-warn">
          <p className="explain-warn-step">
            {fill(dict.explainStoppedAt, { step: dict.explainStoppedAtNames[stopKey] })}
          </p>
          <p>{dict.explainStoppedReasons[stopReasonKey]}</p>
          {result.conflict_rule_codes.length > 0 && (
            <>
              <p className="muted">{dict.conflictingRules}</p>
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
                {dict.auditId} <code>routing.resolve #{result.audit_id}</code>
              </span>
            ) : null}
            {result.routing_rule_id !== null ? (
              <span>
                {dict.ruleId} <code>#{result.routing_rule_id}</code>
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
    { label: dict.checkLabels.coordinates, detail: `${result.latitude.toFixed(4)}, ${result.longitude.toFixed(4)}`, ok: true },
    { label: dict.checkLabels.jurisdiction, detail: result.version_code ?? "CURRENT", ok: Boolean(result.jurisdiction_code) },
    { label: dict.checkLabels.issue, detail: result.issue_type, ok: Boolean(result.routing_rule_code) },
    { label: dict.checkLabels.rule, detail: result.routing_rule_code ?? "—", ok: Boolean(result.routing_rule_code) },
    { label: dict.checkLabels.service, detail: result.service?.code ?? "—", ok: Boolean(result.service) },
  ];

  const steps: ExplainStep[] = [
    {
      icon: "📍",
      label: dict.stepNames.location,
      body: (
        <>
          {dict.coordsLabel} <code>{coords}</code>
          <span className="explain-node-detail"> · {result.issue_type} · {result.effective_date}</span>
        </>
      ),
    },
    {
      icon: "🗺",
      label: dict.stepNames.temporalJurisdiction,
      body: (
        <>
          {jurisdictionValue}
          <span className="explain-node-detail">
            {" "}
            · {fill(dict.versionLabel, { version: result.version_code ?? "(none)" })}
            {result.version_status ? ` (${result.version_status})` : ""}
          </span>
        </>
      ),
    },
    {
      icon: "🗂",
      label: dict.stepNames.wardArea,
      body: (
        <>
          {wardValue}
          {result.matched_scope ? <span className="explain-node-detail"> · {fill(dict.matchedScopeLabel, { scope: result.matched_scope })}</span> : null}
        </>
      ),
    },
    {
      icon: "🏛",
      label: dict.stepNames.authority,
      body: (
        <>
          <strong>{result.authority?.code ?? "(none)"}</strong>
          {result.authority?.name ? <span className="explain-node-detail"> · {result.authority.name}</span> : null}
        </>
      ),
    },
    {
      icon: "🏢",
      label: dict.stepNames.department,
      body: (
        <>
          <strong>{result.department?.code ?? "(none)"}</strong>
          {result.department?.name ? <span className="explain-node-detail"> · {result.department.name}</span> : null}
        </>
      ),
    },
    {
      icon: "🛠",
      label: dict.stepNames.service,
      body: (
        <>
          <strong>{result.service?.code ?? "(none)"}</strong>
          {result.service?.name ? <span className="explain-node-detail"> · {result.service.name}</span> : null}
          {result.sla_days !== null ? <span className="explain-node-detail"> · {fill(dict.slaDays, { days: result.sla_days })}</span> : null}
        </>
      ),
    },
    {
      icon: "📋",
      label: dict.stepNames.routingRule,
      body: (
        <>
          <code>{result.routing_rule_code ?? "(none)"}</code>
          <span className="explain-node-detail"> · {fill(dict.ruleIdNum, { id: result.routing_rule_id ?? "—" })}</span>
        </>
      ),
    },
    {
      icon: "🚨",
      label: dict.stepNames.escalationPath,
      body: (
        <>
          {escalationValue}
          {result.escalation_path.length > 0 && (
            <span className="explain-node-detail">
              {" "}
              · {fill(dict.escalationSteps, { steps: result.escalation_path.map((step) => `#${step.step_number} ${step.authority.code}${step.note ? ` (${step.note})` : ""}`).join(", ") })}
            </span>
          )}
        </>
      ),
    },
  ];

  return (
    <section className="explain-panel" aria-label={dict.explainAriaChosen}>
      <header className="explain-head">
        <h3>{dict.explainTitle}</h3>
        <span className={`result-status ${STATUS_TONE[result.status]}`}>{result.status}</span>
      </header>

      <div className="explain-checks" aria-label={dict.explainDecisionBasis}>
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
          {dict.auditId} <code>{result.audit_id !== null ? `routing.resolve #${result.audit_id}` : "—"}</code>
        </span>
        <span className="explain-map-link">
          {fill(dict.mapFooter, { jurisdiction: result.jurisdiction_code ?? "jurisdiction" })}
        </span>
      </footer>
    </section>
  );
}