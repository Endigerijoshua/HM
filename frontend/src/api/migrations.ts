import { apiGet } from "./client";
import type { MigrationPreviewResponse } from "./migrationTypes";

/** Read-only preview of which OPEN complaints change responsibility under a
 * proposed scenario boundary (P4). */
export function fetchMigrationPreview(scenarioCode: string): Promise<MigrationPreviewResponse> {
  return apiGet<MigrationPreviewResponse>(
    `/whatif/scenarios/${encodeURIComponent(scenarioCode)}/migration-preview`,
  );
}