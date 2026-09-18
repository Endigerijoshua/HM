/** Responsibility conflict detector API types (P5, mirrors backend schemas/conflicts.py). */

export interface ConflictActorRef {
  id: number;
  code: string;
  name: string;
}

export interface ResponsibilityConflict {
  conflict_id: string;
  latitude: number;
  longitude: number;
  complaint_ref: string | null;
  issue_type: string | null;
  issue_type_name: string | null;
  date: string | null;
  jurisdiction_code: string | null;
  jurisdiction_name: string | null;
  expected_authority: ConflictActorRef | null;
  routed_authority: ConflictActorRef | null;
  expected_department: ConflictActorRef | null;
  routed_department: ConflictActorRef | null;
  expected_service: ConflictActorRef | null;
  routed_service: ConflictActorRef | null;
  conflict_type: string;
  severity: string | null;
  explanation: string;
  status: string;
  created_at: string | null;
}

export interface ConflictListResponse {
  count: number;
  conflicts: ResponsibilityConflict[];
}