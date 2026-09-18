/** Civic responsibility routing API types (P2, mirrors backend schemas). */

export type RoutingStatus =
  | "RESOLVED"
  | "RESPONSIBILITY_UNRESOLVED"
  | "NO_JURISDICTION"
  | "TEMPORAL_CONFLICT"
  | "INVALID_LOCATION"
  | "INVALID_ISSUE"
  | "INVALID_DATE";

export interface ActorRef {
  id: number;
  code: string;
  name: string;
}

export interface EscalationStepRef {
  step_number: number;
  authority: ActorRef;
  department: ActorRef;
  service: ActorRef;
  note: string | null;
}

export interface RoutingResult {
  status: RoutingStatus;
  latitude: number;
  longitude: number;
  issue_type: string;
  effective_date: string;

  jurisdiction_code: string | null;
  jurisdiction_name: string | null;
  jurisdiction_kind: string | null;
  version_code: string | null;
  version_status: string | null;
  ward_code: string | null;
  ward_name: string | null;

  matched_scope: string | null;
  authority: ActorRef | null;
  department: ActorRef | null;
  service: ActorRef | null;
  sla_days: number | null;
  routing_rule_code: string | null;
  routing_rule_id: number | null;
  escalation_path: EscalationStepRef[];

  conflict_rule_codes: string[];
  explanation: string | null;
  reason: string | null;
  audit_id: number | null;
}

export interface IssueTypeSummary {
  code: string;
  name: string;
  category: string;
  description: string | null;
  is_active: boolean;
}

export interface IssueTypeListResponse {
  count: number;
  issue_types: IssueTypeSummary[];
}

export interface RoutingRuleSummary {
  id: number;
  code: string;
  issue_type_code: string;
  scope: string;
  priority: number;
  rationale: string;
  effective_from: string;
  effective_to: string | null;
  authority_code: string;
  authority_name: string;
  department_code: string;
  department_name: string;
  service_code: string;
  service_name: string;
  jurisdiction_code: string | null;
  active_on: string | null;
}

export interface RoutingRuleListResponse {
  count: number;
  active_on: string | null;
  issue_type: string | null;
  rules: RoutingRuleSummary[];
}