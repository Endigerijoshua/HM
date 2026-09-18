import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ApiError } from "../api";
import {
  fetchAreas,
  fetchJurisdictions,
  fetchRoads,
  lookupJurisdiction,
} from "../api/gis";
import type {
  AreaSummary,
  JurisdictionLookupResult,
  JurisdictionSummary,
  LookupStatus,
  RoadSummary,
} from "../api/gisTypes";
import { JurisdictionMap } from "../components/map/JurisdictionMap";
import { MapLegend } from "../components/map/MapLegend";

const MIN_DATE = "2020-01-01";
const MAX_DATE = "2026-12-31";
const DEFAULT_DATE = "2024-06-01";

const QUICK_DATES = [
  { label: "V1 · DELIM-2020", date: "2023-06-01" },
  { label: "Gap · no jurisdiction", date: "2024-01-05" },
  { label: "V2 · DELIM-2024", date: "2024-06-01" },
];

type LoadState =
  | { kind: "loading" }
  | { kind: "ok" }
  | { kind: "error"; message: string };

export default function HistoricalExplorerPage() {
  const [searchParams] = useSearchParams();
  const [onDate, setOnDate] = useState(DEFAULT_DATE);
  const [jurisdictions, setJurisdictions] = useState<JurisdictionSummary[]>([]);
  const [areas, setAreas] = useState<AreaSummary[]>([]);
  const [roads, setRoads] = useState<RoadSummary[]>([]);
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [activeVersions, setActiveVersions] = useState<string[]>([]);
  const [probe, setProbe] = useState<{ lat: number; lng: number } | null>(null);
  const [lookup, setLookup] = useState<JurisdictionLookupResult | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [probeLoading, setProbeLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setState({ kind: "loading" });
    Promise.all([fetchAreas(), fetchRoads()])
      .then(([areasRes, roadsRes]) => {
        if (cancelled) return;
        setAreas(areasRes.areas);
        setRoads(roadsRes.roads);
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({
            kind: "error",
            message: error instanceof ApiError ? error.message : "Unknown error",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setState({ kind: "loading" });
    const params: { date: string; includeGeometry: boolean } = {
      date: onDate,
      includeGeometry: true,
    };
    fetchJurisdictions(params)
      .then((response) => {
        if (cancelled) return;
        setJurisdictions(response.jurisdictions);
        setActiveVersions(
          Array.from(new Set(response.jurisdictions.map((j) => j.version_code).filter(Boolean))) as string[],
        );
        setState({ kind: "ok" });
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({
            kind: "error",
            message: error instanceof ApiError ? error.message : "Unknown error",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [onDate]);

  const runLookup = useCallback(
    (lat: number, lng: number, date: string) => {
      setProbe({ lat, lng });
      setProbeLoading(true);
      setLookupError(null);
      setLookup(null);
      lookupJurisdiction({ lat, lng, on_date: date })
        .then((result) => setLookup(result))
        .catch((error: unknown) =>
          setLookupError(error instanceof ApiError ? error.message : "Unknown error"),
        )
        .finally(() => setProbeLoading(false));
    },
    [],
  );

  const handleSelect = (lat: number, lng: number) => {
    runLookup(lat, lng, onDate);
  };

  useEffect(() => {
    const latParam = Number(searchParams.get("lat"));
    const lngParam = Number(searchParams.get("lng"));
    if (Number.isFinite(latParam) && Number.isFinite(lngParam)) {
      runLookup(latParam, lngParam, DEFAULT_DATE);
    }
    // Run once on mount from a deep link (e.g. Citizen Routing → Historical
    // Explorer). Dependencies are intentionally omitted.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const highlightCode = lookup?.jurisdiction?.code ?? null;

  return (
    <section className="page">
      <header className="page-header">
        <h1>Historical Explorer</h1>
        <p>
          Slide across dates to replay jurisdiction versions and probe points on
          the map. Lookups answer geographic containment only; service
          responsibility is <code>NOT_EVALUATED</code> in this phase.
        </p>
      </header>

      <div className="gis-toolbar">
        <div className="gis-toolbar-item">
          <label htmlFor="on-date">Effective date</label>
          <input
            id="on-date"
            type="date"
            min={MIN_DATE}
            max={MAX_DATE}
            value={onDate}
            onChange={(event) => setOnDate(event.target.value)}
          />
        </div>
        <div className="gis-quick">
          {QUICK_DATES.map((q) => (
            <button key={q.date} className="chip" onClick={() => setOnDate(q.date)}>
              {q.label}
            </button>
          ))}
        </div>
        {state.kind === "ok" && (
          <span className="gis-count">{jurisdictions.length} jurisdictions in force</span>
        )}
      </div>

      {state.kind === "error" && <p className="error-text">{state.message}</p>}
      {state.kind === "loading" && <p className="muted">Loading jurisdictions…</p>}

      <div className="gis-layout">
        <div className="card gis-map-card">
          <JurisdictionMap
            jurisdictions={jurisdictions}
            areas={areas}
            roads={roads}
            probe={probe}
            highlightCode={highlightCode}
            activeVersionLabels={activeVersions}
            onSelect={handleSelect}
          />
          <MapLegend />
          <p className="muted gis-click-hint">
            Click anywhere on the map to run a temporal lookup for that point on {onDate}.
          </p>
        </div>

        <div className="card gis-result-card">
          <h3>Lookup result</h3>
          {probeLoading && <p className="muted">Resolving point…</p>}
          {lookupError && <p className="error-text">{lookupError}</p>}
          {!probeLoading && !lookupError && !lookup && (
            <p className="muted">Click a location on the map to begin.</p>
          )}
          {!probeLoading && !lookupError && lookup && <LookupResult lookup={lookup} />}
        </div>
      </div>

      {probe && !probeLoading && !lookupError && lookup?.status === "MATCHED" && (
        <p className="muted gis-demohint">
          Flip point (76.607313, 12.279256): the same coordinate switches boundary
          version and routing rule between DELIM-2020 and DELIM-2024 (with a{" "}
          <code>NO_JURISDICTION</code> gap).{" "}
          <Link to={`/replay?lat=${lookup.lat}&lng=${lookup.lng}&issue=garbage_collection`}>
            Open it in Historical Replay →
          </Link>
        </p>
      )}
    </section>
  );
}

function LookupResult({ lookup }: { lookup: JurisdictionLookupResult }) {
  const statusTone: Record<LookupStatus, string> = {
    MATCHED: "ok-tag",
    NO_JURISDICTION: "muted-tag",
    INVALID_COORDINATES: "bad-tag",
    INVALID_GEOMETRY: "bad-tag",
    TEMPORAL_CONFLICT: "warn-tag",
  };
  return (
    <div className="gis-result">
      <div className="module-head">
        <span className={`result-status ${statusTone[lookup.status]}`}>{lookup.status}</span>
      </div>

      <dl className="kv">
        <div>
          <dt>Point</dt>
          <dd>
            {lookup.lng.toFixed(5)}, {lookup.lat.toFixed(5)}
          </dd>
        </div>
        <div>
          <dt>Date</dt>
          <dd>{lookup.on_date}</dd>
        </div>
        {lookup.jurisdiction && (
          <>
            <div>
              <dt>Jurisdiction</dt>
              <dd>
                {lookup.jurisdiction.code} · {lookup.jurisdiction.kind}
              </dd>
            </div>
            <div>
              <dt>Name</dt>
              <dd>{lookup.jurisdiction.name}</dd>
            </div>
            <div>
              <dt>Version</dt>
              <dd>{lookup.version?.code ?? "—"}</dd>
            </div>
            <div>
              <dt>Version status</dt>
              <dd>{lookup.version?.status ?? "—"}</dd>
            </div>
            {lookup.version && (
              <div>
                <dt>Version window</dt>
                <dd>
                  {lookup.version.effective_from}
                  {lookup.version.effective_to ? ` → ${lookup.version.effective_to}` : " → open"}
                </dd>
              </div>
            )}
          </>
        )}
        {lookup.ward && (
          <div>
            <dt>Ward</dt>
            <dd>
              {lookup.ward.ward_code} · {lookup.ward.name}
            </dd>
          </div>
        )}
        {lookup.corridor && (
          <div>
            <dt>Corridor</dt>
            <dd>
              {lookup.corridor.code} · {lookup.corridor.name}
            </dd>
          </div>
        )}
        {lookup.areas.length > 0 && (
          <div>
            <dt>Areas</dt>
            <dd>{lookup.areas.map((a) => a.code).join(", ")}</dd>
          </div>
        )}
        <div>
          <dt>Responsibility</dt>
          <dd>{lookup.service_responsibility}</dd>
        </div>
      </dl>

      {lookup.version?.status === "SUPERSEDED" && lookup.version.effective_to && (
        <div className="boundary-notice">
          <span className="boundary-badge">BOUNDARY CHANGE</span>
          <span>
            This boundary version was superseded on{" "}
            <strong>{lookup.version.effective_to}</strong> — a newer
            jurisdiction version replaced it. Slide the date forward to see the
            new boundaries.
          </span>
        </div>
      )}

      {lookup.message && <p className="muted">{lookup.message}</p>}
    </div>
  );
}