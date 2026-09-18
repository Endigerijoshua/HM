import { apiGet } from "./client";
import type {
  GraphResolveParams,
  GraphResolveResponse,
} from "./graphTypes";

/** Explanatory responsibility chain for a location + issue + date (P6). */
export function resolveGraph(params: GraphResolveParams): Promise<GraphResolveResponse> {
  const query = new URLSearchParams({
    lat: String(params.lat),
    lng: String(params.lng),
    issue_type: params.issue_type,
    date: params.date,
  });
  return apiGet<GraphResolveResponse>(`/graph/resolve?${query.toString()}`);
}