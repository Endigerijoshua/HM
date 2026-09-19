import { useCallback, useEffect, useRef, useState } from "react";
import {
  type GeolocationStatus,
  isGeolocationSupported,
  LocationError,
  requestCurrentLocation,
  toLocationError,
  type RequestLocationOptions,
} from "../lib/geolocation";

export interface GeolocationState {
  latitude: number | null;
  longitude: number | null;
  accuracy: number | null;
  status: GeolocationStatus;
  error: string | null;
  requestLocation: (options?: RequestLocationOptions) => void;
  reset: () => void;
}

export function useGeolocation(): GeolocationState {
  const [status, setStatus] = useState<GeolocationStatus>(
    isGeolocationSupported() ? "idle" : "unsupported",
  );
  const [coords, setCoords] = useState<{ latitude: number; longitude: number; accuracy: number | null } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef(0);

  const requestLocation = useCallback((options: RequestLocationOptions = {}) => {
    const requestId = ++requestIdRef.current;
    setStatus("requesting");
    setError(null);
    requestCurrentLocation(options)
      .then((location) => {
        if (requestIdRef.current !== requestId) return;
        setCoords(location);
        setStatus("success");
      })
      .catch((err: unknown) => {
        if (requestIdRef.current !== requestId) return;
        const locationError = err instanceof LocationError ? err : toLocationError(err);
        setStatus(locationError.kind);
        setError(locationError.message);
      });
  }, []);

  const reset = useCallback(() => {
    requestIdRef.current += 1;
    setStatus(isGeolocationSupported() ? "idle" : "unsupported");
    setCoords(null);
    setError(null);
  }, []);

  useEffect(() => {
    return () => {
      requestIdRef.current += 1;
    };
  }, []);

  return {
    latitude: coords?.latitude ?? null,
    longitude: coords?.longitude ?? null,
    accuracy: coords?.accuracy ?? null,
    status,
    error,
    requestLocation,
    reset,
  };
}