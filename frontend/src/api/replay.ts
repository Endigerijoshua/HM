import { apiGet } from "./client";
import type { ReplayPointParams, ReplayPointResponse } from "./replayTypes";

/** Chronological responsibility replay for one (location, issue) across a date
 * range (P7). Read-only: never writes audit rows. */
export function fetchReplayPoint(params: ReplayPointParams): Promise<ReplayPointResponse> {
  const query = new URLSearchParams({
    latitude: String(params.latitude),
    longitude: String(params.longitude),
    issue_type: params.issue_type,
    start_date: params.start_date,
    end_date: params.end_date,
  });
  return apiGet<ReplayPointResponse>(`/replay/point?${query.toString()}`);
}