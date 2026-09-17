/** GIS + temporal jurisdiction API types (mirrors backend schemas). */

export type LookupStatus =
  | "MATCHED"
  | "NO_JURISDICTION"
  | "INVALID_COORDINATES"
  | "INVALID_GEOMETRY"
  | "TEMPORAL_CONFLICT";

export type Position = number[];

export interface GeoJsonGeometry {
  type: string;
  coordinates: Position | Position[] | Position[][] | Position[][][];
}

export interface AuthorityRef {
  id: number;
  code: string;
  name: string;
}

export interface JurisdictionVersionRef {
  id: number;
  version_no: number;
  code: string;
  name: string;
  status: string;
  effective_from: string;
  effective_to: string | null;
}

export interface JurisdictionRef {
  id: number;
  code: string;
  name: string;
  kind: string;
  authority: AuthorityRef | null;
  version: JurisdictionVersionRef | null;
}

export interface WardRef {
  id: number;
  ward_code: string;
  name: string;
  locality: string | null;
  jurisdiction_id: number;
}

export interface AreaRef {
  id: number;
  code: string;
  name: string;
  ward_code: string;
  jurisdiction_id: number;
}

export interface CorridorRef {
  id: number;
  code: string;
  name: string;
  road_class: string;
  jurisdiction_id: number;
}

export interface JurisdictionLookupResult {
  status: LookupStatus;
  on_date: string;
  lat: number;
  lng: number;
  jurisdiction: JurisdictionRef | null;
  version: JurisdictionVersionRef | null;
  ward: WardRef | null;
  areas: AreaRef[];
  corridor: CorridorRef | null;
  service_responsibility: string;
  message: string | null;
}

export interface JurisdictionSummary {
  id: number;
  code: string;
  name: string;
  kind: string;
  authority_code: string;
  version_code: string;
  version_status: string;
  effective_from: string;
  effective_to: string | null;
  superseded_by_code: string | null;
  geometry_geojson?: GeoJsonGeometry | null;
}

export interface JurisdictionListResponse {
  count: number;
  on_date: string | null;
  version_id: number | null;
  kind: string | null;
  include_geometry: boolean;
  jurisdictions: JurisdictionSummary[];
}

export interface AreaSummary {
  id: number;
  code: string;
  name: string;
  ward_code: string;
  ward_name: string;
  description: string | null;
  geometry_geojson?: GeoJsonGeometry | null;
}

export interface AreaListResponse {
  count: number;
  areas: AreaSummary[];
}

export interface RoadSummary {
  id: number;
  code: string;
  name: string;
  road_class: string;
  jurisdiction_code: string;
  geometry_geojson?: GeoJsonGeometry | null;
}

export interface RoadListResponse {
  count: number;
  roads: RoadSummary[];
}