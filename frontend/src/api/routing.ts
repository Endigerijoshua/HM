import { apiGet, apiPost } from "./client";
import type {
  IssueTypeListResponse,
  RoutingResult,
  RoutingRuleListResponse,
} from "./routingTypes";

export interface RoutingRuleListParams {
  issueType?: string;
  activeOn?: string;
}

export function fetchIssueTypes(): Promise<IssueTypeListResponse> {
  return apiGet<IssueTypeListResponse>("/routing/issue-types");
}

export function fetchRoutingRules(params: RoutingRuleListParams): Promise<RoutingRuleListResponse> {
  const query = new URLSearchParams();
  if (params.issueType) query.set("issue_type", params.issueType);
  if (params.activeOn) query.set("active_on", params.activeOn);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiGet<RoutingRuleListResponse>(`/routing/rules${suffix}`);
}

export function resolveRoute(payload: {
  lat: number;
  lng: number;
  issue_type: string;
  date: string;
}): Promise<RoutingResult> {
  return apiPost<RoutingResult>("/routing/resolve", {
    latitude: payload.lat,
    longitude: payload.lng,
    issue_type: payload.issue_type,
    date: payload.date,
  });
}