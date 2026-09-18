export type {
  ApiErrorBody,
  ApiErrorDetail,
  ApiHealth,
} from "./types";
export { ApiError, API_BASE, apiGet, apiPost, fetchHealth } from "./client";
export {
  fetchAreas,
  fetchJurisdictions,
  fetchRoads,
  lookupJurisdiction,
} from "./gis";
export type { JurisdictionListParams } from "./gis";
export type {
  AreaListResponse,
  AreaRef,
  AreaSummary,
  CorridorRef,
  GeoJsonGeometry,
  JurisdictionListResponse,
  JurisdictionLookupResult,
  JurisdictionRef,
  JurisdictionSummary,
  JurisdictionVersionRef,
  LookupStatus,
  Position,
  RoadListResponse,
  RoadSummary,
  WardRef,
} from "./gisTypes";
export {
  fetchIssueTypes,
  fetchRoutingRules,
  resolveRoute,
} from "./routing";
export type { RoutingRuleListParams } from "./routing";
export type {
  ActorRef,
  EscalationStepRef,
  IssueTypeListResponse,
  IssueTypeSummary,
  RoutingResult,
  RoutingRuleListResponse,
  RoutingRuleSummary,
  RoutingStatus,
} from "./routingTypes";