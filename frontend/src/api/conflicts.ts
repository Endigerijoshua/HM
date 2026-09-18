import { apiGet } from "./client";
import type { ConflictListResponse } from "./conflictsTypes";

/** List persisted responsibility conflicts (P5). Read-only. */
export function fetchConflicts(): Promise<ConflictListResponse> {
  return apiGet<ConflictListResponse>("/conflicts");
}