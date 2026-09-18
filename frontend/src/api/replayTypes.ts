/** Historical jurisdiction replay API types (P7, mirrors backend schemas/replay.py). */

export type ReplayStatus =
  | "RESOLVED"
  | "RESPONSIBILITY_UNRESOLVED"
  | "NO_JURISDICTION"
  | "TEMPORAL_CONFLICT"
  | "INVALID_LOCATION"
  | "INVALID_ISSUE"
  | "INVALID_DATE";

export interface ReplayActorRef {
  id: number;
  code: string;
  name: string;
}

/** One maximal run of days (closed-open [effective_from, effective_to)) where
 * the resolved jurisdiction/responsibility state did not change. */
export interface ReplayPeriod {
  effective_from: string;
  effective_to: string;
  status: ReplayStatus;
  boundary_change: boolean;

  jurisdiction_code: string | null;
  jurisdiction_name: string | null;
  jurisdiction_kind: string | null;
  version_code: string | null;
  version_status: string | null;
  ward_code: string | null;
  ward_name: string | null;

  matched_scope: string | null;
  authority: ReplayActorRef | null;
  department: ReplayActorRef | null;
  service: ReplayActorRef | null;
  routing_rule_code: string | null;
  routing_rule_id: number | null;
  conflict_rule_codes: string[];

  explanation: string | null;
  reason: string | null;
  chain: string | null;
}

export interface ReplayPointResponse {
  status: string;
  latitude: number;
  longitude: number;
  issue_type: string;
  start_date: string;
  end_date: string;
  day_count: number;
  period_count: number;
  jurisdiction_change_count: number;
  periods: ReplayPeriod[];
}

export interface ReplayPointParams {
  latitude: number;
  longitude: number;
  issue_type: string;
  start_date: string;
  end_date: string;
}