import { apiGet, apiPost } from "./client";
import type {
  AreaListResponse,
  JurisdictionListResponse,
  JurisdictionLookupResult,
  RoadListResponse,
} from "./gisTypes";

export interface JurisdictionListParams {
  date?: string;
  versionId?: number;
  kind?: string;
  includeGeometry?: boolean;
}

export function fetchJurisdictions(params: JurisdictionListParams): Promise<JurisdictionListResponse> {
  const query = new URLSearchParams();
  if (params.date) query.set("date", params.date);
  if (params.versionId !== undefined) query.set("version_id", String(params.versionId));
  if (params.kind) query.set("kind", params.kind);
  if (params.includeGeometry) query.set("include_geometry", "true");
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiGet<JurisdictionListResponse>(`/gis/jurisdictions${suffix}`);
}

export function lookupJurisdiction(payload: {
  lat: number;
  lng: number;
  on_date: string;
}): Promise<JurisdictionLookupResult> {
  return apiPost<JurisdictionLookupResult>("/gis/lookup", payload);
}

export function fetchAreas(): Promise<AreaListResponse> {
  return apiGet<AreaListResponse>("/gis/areas");
}

export function fetchRoads(): Promise<RoadListResponse> {
  return apiGet<RoadListResponse>("/gis/roads");
}