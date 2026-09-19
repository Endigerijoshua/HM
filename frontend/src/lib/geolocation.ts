export type GeolocationStatus =
  | "idle"
  | "requesting"
  | "success"
  | "permission-denied"
  | "unavailable"
  | "timeout"
  | "unsupported"
  | "error";

export type LocationErrorKind = Exclude<
  GeolocationStatus,
  "idle" | "requesting" | "success"
>;

export type LocationSource = "gps" | "map" | "manual";

export interface DetectedLocation {
  latitude: number;
  longitude: number;
  accuracy: number | null;
}

export interface SelectedLocation {
  latitude: number;
  longitude: number;
  accuracy: number | null;
  source: LocationSource;
}

export interface GeolocationPositionLike {
  coords: {
    latitude: number;
    longitude: number;
    accuracy: number;
  };
}

export interface GeolocationErrorLike {
  code: number;
  PERMISSION_DENIED: number;
  POSITION_UNAVAILABLE: number;
  TIMEOUT: number;
  message: string;
}

export interface GeolocationProvider {
  getCurrentPosition(
    success: (position: GeolocationPositionLike) => void,
    error: (err: GeolocationErrorLike) => void,
    options?: {
      enableHighAccuracy?: boolean;
      timeout?: number;
      maximumAge?: number;
    },
  ): void;
}

export const GEOLOCATION_TIMEOUT_MS = 10000;
export const GEOLOCATION_MAXIMUM_AGE_MS = 0;
export const GEOLOCATION_ENABLE_HIGH_ACCURACY = true;

export const GEOLOCATION_MESSAGES: Record<LocationErrorKind, string> = {
  "permission-denied":
    "Location permission was denied. Turn on location access for this site in your browser settings, then try again.",
  unavailable: "Your location could not be determined right now. Try again in a moment.",
  timeout: "Getting your location is taking too long. Check your connection and try again.",
  unsupported: "Location detection is not supported by this browser or device.",
  error: "We couldn't get your location. Please try again or use the map or manual entry instead.",
};

export class LocationError extends Error {
  readonly kind: LocationErrorKind;

  constructor(kind: LocationErrorKind) {
    super(GEOLOCATION_MESSAGES[kind]);
    this.name = "LocationError";
    this.kind = kind;
  }
}

export function toLocationError(err: unknown): LocationError {
  if (err instanceof LocationError) return err;
  const code = (err as Partial<GeolocationErrorLike> | null)?.code;
  if (code === 1) return new LocationError("permission-denied");
  if (code === 2) return new LocationError("unavailable");
  if (code === 3) return new LocationError("timeout");
  return new LocationError("error");
}

export function isGeolocationSupported(): boolean {
  return typeof navigator !== "undefined" && typeof navigator.geolocation !== "undefined";
}

export interface RequestLocationOptions {
  enableHighAccuracy?: boolean;
  timeout?: number;
  maximumAge?: number;
  /** Injectable for tests; falls back to navigator.geolocation when omitted. */
  provider?: GeolocationProvider | null;
}

export function requestCurrentLocation(
  options: RequestLocationOptions = {},
): Promise<DetectedLocation> {
  const provider = options.provider ?? (isGeolocationSupported() ? navigator.geolocation : null);

  if (!provider) {
    return Promise.reject(new LocationError("unsupported"));
  }

  return new Promise<DetectedLocation>((resolve, reject) => {
    provider.getCurrentPosition(
      (position) => {
        resolve({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: Number.isFinite(position.coords.accuracy)
            ? position.coords.accuracy
            : null,
        });
      },
      (err) => {
        reject(toLocationError(err));
      },
      {
        enableHighAccuracy: options.enableHighAccuracy ?? GEOLOCATION_ENABLE_HIGH_ACCURACY,
        timeout: options.timeout ?? GEOLOCATION_TIMEOUT_MS,
        maximumAge: options.maximumAge ?? GEOLOCATION_MAXIMUM_AGE_MS,
      },
    );
  });
}