/** Responsibility graph API types (P6, mirrors backend schemas/graph.py). */

export type GraphNodeType =
  | "LOCATION"
  | "JURISDICTION"
  | "AUTHORITY"
  | "DEPARTMENT"
  | "SERVICE"
  | "ISSUE"
  | "ESCALATION";

export type GraphEdgeType =
  | "RESPONSIBLE_FOR"
  | "MANAGED_BY"
  | "HANDLED_BY"
  | "ESCALATES_TO";

export interface GraphNode {
  id: string;
  type: GraphNodeType;
  label: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: GraphEdgeType;
  label: string | null;
}

export interface GraphResolveResponse {
  status: string;
  latitude: number;
  longitude: number;
  issue_type: string;
  date: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  routing_id: number | null;
  routing_rule_id: number | null;
  explanation: string;
}

export interface GraphResolveParams {
  lat: number;
  lng: number;
  issue_type: string;
  date: string;
}