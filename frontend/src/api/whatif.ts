import { apiGet, apiPost } from "./client";
import type {
  WhatIfScenarioListResponse,
  WhatIfSimulateResponse,
} from "./whatifTypes";

export function fetchWhatIfScenarios(): Promise<WhatIfScenarioListResponse> {
  return apiGet<WhatIfScenarioListResponse>("/whatif/scenarios");
}

export function simulateWhatIf(payload: {
  longitude: number;
  latitude: number;
  issue_type_code: string;
  on_date: string;
}): Promise<WhatIfSimulateResponse> {
  return apiPost<WhatIfSimulateResponse>("/whatif/simulate", payload);
}
