import type { ApiErrorBody, ApiHealth } from "./types";

/** Base URL of the backend REST API (v1). */
export const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

/** Error raised for network failures and non-2xx API responses. */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: unknown[];

  constructor(status: number, code: string, message: string, details: unknown[] = []) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
      ...init,
    });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "Backend is unreachable. Is the API running?");
  }

  const text = await response.text();
  let body: unknown = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = null;
  }

  if (!response.ok) {
    const error = (body as ApiErrorBody | null)?.error;
    throw new ApiError(
      response.status,
      error?.code ?? "HTTP_ERROR",
      error?.message ?? response.statusText,
      error?.details ?? [],
    );
  }

  return body as T;
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path);
}

export function apiPost<T>(path: string, payload: unknown): Promise<T> {
  return request<T>(path, { method: "POST", body: JSON.stringify(payload) });
}

export async function fetchHealth(): Promise<ApiHealth> {
  return apiGet<ApiHealth>("/health");
}