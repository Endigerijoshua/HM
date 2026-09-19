/** Complaint migration preview API types (P4, mirrors backend schemas/whatif.py). */

export interface MigrationComplaint {
  complaint_id: number;
  public_ref: string;
  issue_type: string;
  issue_type_name: string | null;
  latitude: number;
  longitude: number;
  status: string;
  in_proposed_boundary: boolean;
  current_jurisdiction_code: string | null;
  current_jurisdiction_name: string | null;
  current_ward_code: string | null;
  current_ward_name: string | null;
  current_authority_code: string | null;
  current_authority_name: string | null;
  current_department_code: string | null;
  current_department_name: string | null;
  current_service_code: string | null;
  current_service_name: string | null;
  proposed_jurisdiction_code: string | null;
  proposed_jurisdiction_name: string | null;
  proposed_ward_code: string | null;
  proposed_ward_name: string | null;
  proposed_authority_code: string | null;
  proposed_authority_name: string | null;
  proposed_department_code: string | null;
  proposed_department_name: string | null;
  proposed_service_code: string | null;
  proposed_service_name: string | null;
  migration_required: boolean;
  responsibility_changed: boolean;
  explanation: string;
}

export interface MigrationPreviewResponse {
  scenario_code: string;
  scenario_name: string;
  preview_date: string;
  total_open_complaints: number;
  affected_count: number;
  responsibility_change_count: number;
  complaints: MigrationComplaint[];
}
