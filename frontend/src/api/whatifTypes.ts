/** What-If scenario simulator API types (P3, mirrors backend schemas). */

import type { RoutingResult } from "./routingTypes";

export type WhatIfScenarioStatus =
  | "DRAFT"
  | "SIMULATED"
  | "APPLIED"
  | "DISCARDED";

export interface WhatIfScenarioSummary {
  id: number;
  code: string;
  name: string;
  description: string | null;
  status: WhatIfScenarioStatus;
  applies_to: string | null;
  affected_region_name: string | null;
  geometry_geojson: Record<string, unknown> | null;
  envelope_geojson: Record<string, unknown> | null;
  result_summary: Record<string, unknown> | null;
  created_at: string;
}

export interface WhatIfScenarioListResponse {
  count: number;
  scenarios: WhatIfScenarioSummary[];
}

export interface ImpactMetric {
  label: string;
  current: number;
  proposed: number;
  delta: number;
}

export interface ResponsibilityDelta {
  issue_type_code: string;
  issue_type_name: string;
  longitude: number;
  latitude: number;
  on_date: string;
  status: string;
  matched_scope: string | null;
  authority_code: string | null;
  authority_name: string | null;
  department_code: string | null;
  department_name: string | null;
  service_code: string | null;
  service_name: string | null;
  routing_rule_code: string | null;
  conflict_rule_codes: string[];
  description: string;
}

export interface WhatIfComplaintRef {
  public_ref: string;
  issue_type_code: string;
  latitude: number;
  longitude: number;
  ward_code: string | null;
  ward_name: string | null;
}

export interface WhatIfSimulateResponse {
  scenario_code: string;
  scenario_name: string;
  in_proposed_geometry: boolean;
  on_date: string;
  current: RoutingResult;
  proposed: RoutingResult | null;
  responsibility_deltas: ResponsibilityDelta[];
  affected_complaint_count: number;
  impact: ImpactMetric[];
  potential_conflicts: string[];
}
