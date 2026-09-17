/** API contract types shared with the FastAPI backend. */

export interface ApiHealth {
  status: string;
  app_name: string;
  app_version: string;
  database_status: string;
  seed_loaded: boolean;
  geometry_engine: string;
  timestamp: string;
}

export interface ApiErrorDetail {
  loc?: string | null;
  message: string;
  type?: string | null;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details: ApiErrorDetail[];
  };
}