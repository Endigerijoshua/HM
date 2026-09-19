import { useMemo, useEffect, useRef, useState } from "react";
import type { KeyboardEvent as ReactKeyboardEvent, MouseEvent as ReactMouseEvent, PointerEvent as ReactPointerEvent } from "react";
import type {
  GeoJsonGeometry,
  JurisdictionSummary,
  Position,
} from "../../api/gisTypes";
import type { SelectedLocation } from "../../lib/geolocation";

const VIEW_W = 960;
const VIEW_H = 600;
const PAD = 48;

const METERS_PER_DEG_LAT = 111320;

const MIN_K = 1;
const MAX_K = 14;
const DRAG_SLOP = 5;

const DEMO_BOUNDS = {
  minLon: 76.4,
  maxLon: 76.92,
  minLat: 12.1,
  maxLat: 12.45,
};

interface Bounds {
  minLon: number;
  maxLon: number;
  minLat: number;
  maxLat: number;
}

interface ViewState {
  x: number;
  y: number;
  k: number;
}

const VIEW_IDENTITY: ViewState = { x: 0, y: 0, k: 1 };

function clampK(k: number): number {
  return Math.min(MAX_K, Math.max(MIN_K, k));
}

function zoomAt(view: ViewState, vx: number, vy: number, factor: number): ViewState {
  const nextK = clampK(view.k * factor);
  const f = nextK / view.k;
  return { k: nextK, x: vx + (view.x - vx) * f, y: vy + (view.y - vy) * f };
}

function viewToWorld(view: ViewState, vx: number, vy: number): { x: number; y: number } {
  return { x: (vx - view.x) / view.k, y: (vy - view.y) / view.k };
}

interface ShapeSet {
  paths: string[];
  polylines: string[];
  points: Position[];
  label: { x: number; y: number; text: string } | null;
}

const KIND_FILL: Record<string, { fill: string; stroke: string; dash?: string }> = {
  WARD: { fill: "#ccfbf1", stroke: "#0f766e" },
  SPECIAL_CORRIDOR: { fill: "rgba(245,158,11,0.10)", stroke: "#b45309", dash: "6 4" },
  HERITAGE_ZONE: { fill: "rgba(217,119,6,0.12)", stroke: "#d97706" },
};

const DEFAULT_STYLE = { fill: "#e2e8f0", stroke: "#94a3b8" };

interface MapProps {
  jurisdictions: JurisdictionSummary[];
  areas: { code: string; name: string; geometry_geojson?: GeoJsonGeometry | null }[];
  roads: { code: string; name: string; geometry_geojson?: GeoJsonGeometry | null }[];
  probe: { lat: number; lng: number } | null;
  highlightCode: string | null;
  activeVersionLabels: string[];
  proposedGeometry?: GeoJsonGeometry | null;
  proposedLabel?: string | null;
  onSelect: (lat: number, lng: number) => void;
  interactive?: boolean;
  selectedLocation?: SelectedLocation | null;
  focusLocation?: { lat: number; lng: number } | null;
  picking?: boolean;
}

function collectCoords(coords: unknown, out: Position[]): void {
  if (!Array.isArray(coords)) return;
  if (coords.length >= 2 && typeof coords[0] === "number" && typeof coords[1] === "number") {
    out.push([coords[0], coords[1]]);
    return;
  }
  for (const entry of coords) collectCoords(entry as unknown, out);
}

function computeBounds(
  jurisdictions: JurisdictionSummary[],
  areas: { geometry_geojson?: GeoJsonGeometry | null }[],
  roads: { geometry_geojson?: GeoJsonGeometry | null }[],
  proposedGeometry?: GeoJsonGeometry | null,
): Bounds {
  const pts: Position[] = [];
  for (const j of jurisdictions) if (j.geometry_geojson) collectCoords(j.geometry_geojson.coordinates, pts);
  for (const a of areas) if (a.geometry_geojson) collectCoords(a.geometry_geojson.coordinates, pts);
  for (const r of roads) if (r.geometry_geojson) collectCoords(r.geometry_geojson.coordinates, pts);
  if (proposedGeometry) collectCoords(proposedGeometry.coordinates, pts);
  if (pts.length === 0) return DEMO_BOUNDS;
  const lons = pts.map((p) => p[0]);
  const lats = pts.map((p) => p[1]);
  const span = Math.max(Math.max(...lons) - Math.min(...lons), Math.max(...lats) - Math.min(...lats), 0.02);
  const cx = (Math.min(...lons) + Math.max(...lons)) / 2;
  const cy = (Math.min(...lats) + Math.max(...lats)) / 2;
  return { minLon: cx - span / 2, maxLon: cx + span / 2, minLat: cy - span / 2, maxLat: cy + span / 2 };
}

function project(lon: number, lat: number, b: Bounds): { x: number; y: number } {
  const x = PAD + ((lon - b.minLon) / (b.maxLon - b.minLon)) * (VIEW_W - 2 * PAD);
  const y = PAD + ((b.maxLat - lat) / (b.maxLat - b.minLat)) * (VIEW_H - 2 * PAD);
  return { x, y };
}

function ringPath(ring: Position[], b: Bounds): string {
  if (ring.length < 2) return "";
  const start = project(ring[0][0], ring[0][1], b);
  let d = `M ${start.x.toFixed(2)} ${start.y.toFixed(2)}`;
  for (let i = 1; i < ring.length; i += 1) {
    const p = project(ring[i][0], ring[i][1], b);
    d += ` L ${p.x.toFixed(2)} ${p.y.toFixed(2)}`;
  }
  return `${d} Z`;
}

function linePath(line: Position[], b: Bounds): string {
  return ringPath(line, b).replace(/ Z$/, "");
}

function geometryToShapes(geom: GeoJsonGeometry | undefined, b: Bounds, labelText?: string): ShapeSet {
  const shapes: ShapeSet = { paths: [], polylines: [], points: [], label: null };
  if (!geom) return shapes;
  const coords = geom.coordinates as Position[][][] | Position[][] | Position[];

  let centroidX = 0;
  let centroidY = 0;
  let count = 0;

  if (geom.type === "Polygon") {
    for (const ring of coords as Position[][]) {
      shapes.paths.push(ringPath(ring as Position[], b));
      for (const pt of ring as Position[]) {
        const p = project(pt[0], pt[1], b);
        centroidX += p.x;
        centroidY += p.y;
        count += 1;
      }
    }
  } else if (geom.type === "MultiPolygon") {
    for (const poly of coords as Position[][][]) {
      for (const ring of poly as Position[][]) {
        shapes.paths.push(ringPath(ring as Position[], b));
        for (const pt of ring as Position[]) {
          const p = project(pt[0], pt[1], b);
          centroidX += p.x;
          centroidY += p.y;
          count += 1;
        }
      }
    }
  } else if (geom.type === "LineString") {
    shapes.polylines.push(linePath(coords as Position[], b));
  } else if (geom.type === "MultiLineString") {
    for (const line of coords as Position[][]) shapes.polylines.push(linePath(line as Position[], b));
  } else if (geom.type === "Point") {
    shapes.points.push(coords as unknown as Position);
  } else if (geom.type === "MultiPoint") {
    shapes.points.push(...(coords as Position[]));
  }

  if (labelText && count > 0) {
    shapes.label = { x: centroidX / count, y: centroidY / count, text: labelText };
  }
  return shapes;
}

function overlayPaths(
  items: { code: string; geometry_geojson?: GeoJsonGeometry | null }[],
  b: Bounds,
): string[] {
  const paths: string[] = [];
  for (const item of items) {
    if (!item.geometry_geojson) continue;
    const shapes = geometryToShapes(item.geometry_geojson ?? undefined, b);
    paths.push(...shapes.polylines, ...shapes.paths);
  }
  return paths;
}

function accuracyViewRadius(selected: SelectedLocation, b: Bounds): number {
  if (selected.accuracy == null || selected.accuracy <= 0 || !Number.isFinite(selected.accuracy)) {
    return 0;
  }
  const degLat = selected.accuracy / METERS_PER_DEG_LAT;
  const degLon =
    selected.accuracy / (METERS_PER_DEG_LAT * Math.cos((selected.latitude * Math.PI) / 180));
  const c = project(selected.longitude, selected.latitude, b);
  const rx = Math.abs(project(selected.longitude + degLon, selected.latitude, b).x - c.x);
  const ry = Math.abs(project(selected.longitude, selected.latitude + degLat, b).y - c.y);
  return Math.max(Math.max(rx, ry), 4);
}

function clampLat(lat: number): number {
  return Math.min(90, Math.max(-90, lat));
}

function clampLon(lon: number): number {
  return Math.min(180, Math.max(-180, lon));
}

export function JurisdictionMap({
  jurisdictions,
  areas,
  roads,
  probe,
  highlightCode,
  activeVersionLabels,
  proposedGeometry,
  proposedLabel,
  onSelect,
  interactive = false,
  selectedLocation = null,
  focusLocation = null,
  picking = false,
}: MapProps) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [view, setView] = useState<ViewState>(VIEW_IDENTITY);
  const viewRef = useRef<ViewState>(view);
  viewRef.current = view;

  const pointersRef = useRef(new Map<number, { vx: number; vy: number }>());
  const gestureRef = useRef<{ mode: "none" | "pan" | "pinch"; moved: boolean; startVx: number; startVy: number }>({
    mode: "none",
    moved: false,
    startVx: 0,
    startVy: 0,
  });
  const lastFocusRef = useRef<string | null>(null);

  const bounds = useMemo(
    () => computeBounds(jurisdictions, areas, roads, proposedGeometry),
    [jurisdictions, areas, roads, proposedGeometry],
  );

  const layers = useMemo(() => {
    const areaPaths = overlayPaths(areas, bounds);
    const roadPaths = overlayPaths(roads, bounds);

    const wards: { d: string; stroke: string; fill: string; code: string; highlight: boolean }[] = [];
    const others: { d: string; stroke: string; fill: string; dash?: string; code: string }[] = [];
    const labels: { x: number; y: number; text: string }[] = [];

    const proposed = proposedGeometry
      ? geometryToShapes(proposedGeometry, bounds, proposedLabel ?? undefined)
      : null;

    for (const j of jurisdictions) {
      const style = KIND_FILL[j.kind] ?? DEFAULT_STYLE;
      const shapes = geometryToShapes(j.geometry_geojson ?? undefined, bounds, j.code);
      for (const d of shapes.paths) {
        if (j.kind === "WARD") {
          wards.push({ d, stroke: style.stroke, fill: style.fill, code: j.code, highlight: j.code === highlightCode });
        } else {
          others.push({ d, stroke: style.stroke, fill: style.fill, dash: style.dash, code: j.code });
        }
      }
      if (shapes.label) labels.push(shapes.label);
    }
    return { areaPaths, roadPaths, wards, others, labels, proposed };
  }, [jurisdictions, areas, roads, bounds, highlightCode, proposedGeometry, proposedLabel]);

  const clientToView = (clientX: number, clientY: number): { vx: number; vy: number } => {
    const svg = svgRef.current;
    if (!svg) return { vx: 0, vy: 0 };
    const rect = svg.getBoundingClientRect();
    const scaleX = rect.width ? VIEW_W / rect.width : 1;
    const scaleY = rect.height ? VIEW_H / rect.height : 1;
    return { vx: (clientX - rect.left) * scaleX, vy: (clientY - rect.top) * scaleY };
  };

  const worldPosToLonLat = (wx: number, wy: number): { lat: number; lng: number } => {
    const lon = bounds.minLon + ((wx - PAD) / (VIEW_W - 2 * PAD)) * (bounds.maxLon - bounds.minLon);
    const lat = bounds.maxLat - ((wy - PAD) / (VIEW_H - 2 * PAD)) * (bounds.maxLat - bounds.minLat);
    return { lat: clampLat(lat), lng: clampLon(lon) };
  };

  const handleClick = (event: ReactMouseEvent<SVGSVGElement>) => {
    const { vx, vy } = clientToView(event.clientX, event.clientY);
    const { lat, lng } = worldPosToLonLat(vx, vy);
    onSelect(lat, lng);
  };

  const handlePointerDown = (event: ReactPointerEvent<SVGSVGElement>) => {
    if (event.button !== 0 && event.pointerType !== "touch") return;
    svgRef.current?.setPointerCapture?.(event.pointerId);
    const { vx, vy } = clientToView(event.clientX, event.clientY);
    pointersRef.current.set(event.pointerId, { vx, vy });
    const count = pointersRef.current.size;
    if (count === 1) {
      gestureRef.current.mode = "none";
      gestureRef.current.moved = false;
      gestureRef.current.startVx = vx;
      gestureRef.current.startVy = vy;
    } else if (count === 2) {
      gestureRef.current.mode = "pinch";
    }
  };

  const handlePointerMove = (event: ReactPointerEvent<SVGSVGElement>) => {
    const prev = pointersRef.current.get(event.pointerId);
    if (!prev) return;
    const { vx, vy } = clientToView(event.clientX, event.clientY);
    const g = gestureRef.current;
    const pointers = pointersRef.current;

    if (pointers.size === 1) {
      const dx = vx - prev.vx;
      const dy = vy - prev.vy;
      pointersRef.current.set(event.pointerId, { vx, vy });
      if (g.mode === "pan") {
        setView((v) => ({ ...v, x: v.x + dx, y: v.y + dy }));
        return;
      }
      if (!g.moved && Math.hypot(vx - g.startVx, vy - g.startVy) > DRAG_SLOP) {
        g.mode = "pan";
        g.moved = true;
      }
      return;
    }

    if (pointers.size === 2) {
      const entries = [...pointers.entries()];
      const [idA, prevA] = entries[0];
      const [idB, prevB] = entries[1];
      const curA = idA === event.pointerId ? { vx, vy } : prevA;
      const curB = idB === event.pointerId ? { vx, vy } : prevB;
      pointersRef.current.set(event.pointerId, { vx, vy });
      const prevDist = Math.hypot(prevB.vx - prevA.vx, prevB.vy - prevA.vy);
      const curDist = Math.hypot(curB.vx - curA.vx, curB.vy - curA.vy);
      if (prevDist > 0 && curDist > 0) {
        const midX = (curA.vx + curB.vx) / 2;
        const midY = (curA.vy + curB.vy) / 2;
        setView((v) => zoomAt(v, midX, midY, curDist / prevDist));
      }
    }
  };

  const endPointer = (event: ReactPointerEvent<SVGSVGElement>, asTap: boolean) => {
    const pointers = pointersRef.current;
    const g = gestureRef.current;
    const isTapCandidate = asTap && !g.moved && pointers.size === 1 && g.mode === "none";
    pointers.delete(event.pointerId);
    if (pointers.size === 0) {
      if (isTapCandidate) {
        const world = viewToWorld(viewRef.current, g.startVx, g.startVy);
        const { lat, lng } = worldPosToLonLat(world.x, world.y);
        onSelect(lat, lng);
      }
      gestureRef.current = { mode: "none", moved: false, startVx: 0, startVy: 0 };
    } else if (pointers.size === 1) {
      const [remaining] = [...pointers.values()];
      gestureRef.current = {
        mode: "none",
        moved: false,
        startVx: remaining.vx,
        startVy: remaining.vy,
      };
    }
  };

  const handlePointerUp = (event: ReactPointerEvent<SVGSVGElement>) => endPointer(event, true);
  const handlePointerCancel = (event: ReactPointerEvent<SVGSVGElement>) => endPointer(event, false);

  useEffect(() => {
    if (!interactive) return;
    const svg = svgRef.current;
    if (!svg) return;
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      const { vx, vy } = clientToView(event.clientX, event.clientY);
      const factor = Math.exp(-event.deltaY * 0.0015);
      setView((v) => zoomAt(v, vx, vy, factor));
    };
    svg.addEventListener("wheel", onWheel, { passive: false });
    return () => svg.removeEventListener("wheel", onWheel);
  }, [interactive]);

  useEffect(() => {
    if (!interactive || !focusLocation) return;
    const key = `${focusLocation.lat.toFixed(6)},${focusLocation.lng.toFixed(6)}`;
    if (lastFocusRef.current === key) return;
    lastFocusRef.current = key;
    const world = project(focusLocation.lng, focusLocation.lat, bounds);
    setView((v) => {
      const k = Math.max(v.k, 1.2);
      return { k, x: VIEW_W / 2 - world.x * k, y: VIEW_H / 2 - world.y * k };
    });
  }, [interactive, focusLocation, bounds]);

  const zoomBy = (factor: number) => {
    setView((v) => zoomAt(v, VIEW_W / 2, VIEW_H / 2, factor));
  };

  const handleKeyDown = (event: ReactKeyboardEvent<SVGSVGElement>) => {
    if (!interactive) return;
    const step = 40;
    switch (event.key) {
      case "ArrowLeft":
        event.preventDefault();
        setView((v) => ({ ...v, x: v.x + step }));
        break;
      case "ArrowRight":
        event.preventDefault();
        setView((v) => ({ ...v, x: v.x - step }));
        break;
      case "ArrowUp":
        event.preventDefault();
        setView((v) => ({ ...v, y: v.y + step }));
        break;
      case "ArrowDown":
        event.preventDefault();
        setView((v) => ({ ...v, y: v.y - step }));
        break;
      case "+":
      case "=":
      case "PageUp":
        event.preventDefault();
        zoomBy(1.35);
        break;
      case "-":
      case "PageDown":
        event.preventDefault();
        zoomBy(1 / 1.35);
        break;
      case "Enter":
      case " ":
        event.preventDefault();
        if (picking) {
          const world = viewToWorld(viewRef.current, VIEW_W / 2, VIEW_H / 2);
          const { lat, lng } = worldPosToLonLat(world.x, world.y);
          onSelect(lat, lng);
        }
        break;
    }
  };

  const probePos = probe ? project(probe.lng, probe.lat, bounds) : null;
  const selectedPos = selectedLocation
    ? project(selectedLocation.longitude, selectedLocation.latitude, bounds)
    : null;
  const selectedAccuracyR =
    selectedLocation && selectedLocation.accuracy != null && selectedLocation.accuracy > 0
      ? accuracyViewRadius(selectedLocation, bounds)
      : 0;

  return (
    <div className={`jurisdiction-map-shell${interactive ? " is-interactive" : ""}${picking ? " is-picking" : ""}`}>
      {interactive && (
        <div className="map-controls" aria-label="Map controls">
          <button type="button" className="map-control-btn" onClick={() => zoomBy(1.35)} aria-label="Zoom in" title="Zoom in">
            +
          </button>
          <button type="button" className="map-control-btn" onClick={() => zoomBy(1 / 1.35)} aria-label="Zoom out" title="Zoom out">
            &minus;
          </button>
          <button type="button" className="map-control-btn" onClick={() => setView(VIEW_IDENTITY)} aria-label="Reset view" title="Reset view">
            &times;
          </button>
        </div>
      )}
      <svg
        ref={svgRef}
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        className="gis-map"
        onClick={interactive ? undefined : handleClick}
        onPointerDown={interactive ? handlePointerDown : undefined}
        onPointerMove={interactive ? handlePointerMove : undefined}
        onPointerUp={interactive ? handlePointerUp : undefined}
        onPointerCancel={interactive ? handlePointerCancel : undefined}
        onKeyDown={interactive ? handleKeyDown : undefined}
        tabIndex={interactive ? 0 : undefined}
        role="img"
        aria-label={
          interactive
            ? "Interactive jurisdiction map. Drag or use arrow keys to pan, scroll or pinch to zoom, tap to select a location."
            : "Jurisdiction map"
        }
      >
        <rect x="0" y="0" width={VIEW_W} height={VIEW_H} fill="#eaf3ee" />

        <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>
          {layers.areaPaths.map((d, i) => (
            <path key={`a${i}`} d={d} fill="rgba(79,70,229,0.10)" stroke="#4f46e5" strokeWidth={1.5} />
          ))}

          {layers.wards.map((w, i) => (
            <path
              key={`w${i}`}
              d={w.d}
              fill={w.fill}
              stroke={w.highlight ? "#111827" : w.stroke}
              strokeWidth={w.highlight ? 3 : 2}
              opacity={w.highlight ? 1 : 0.75}
            />
          ))}

          {layers.others.map((o, i) => (
            <path
              key={`o${i}`}
              d={o.d}
              fill={o.fill}
              stroke={o.stroke}
              strokeWidth={2}
              strokeDasharray={o.dash}
            />
          ))}

          {layers.roadPaths.map((d, i) => (
            <path
              key={`r${i}`}
              d={d}
              fill="none"
              stroke="#15803d"
              strokeWidth={5}
              strokeLinecap="round"
              opacity={0.85}
            />
          ))}

          {layers.proposed && (
            <>
              {layers.proposed.paths.map((d, i) => (
                <path
                  key={`p${i}`}
                  d={d}
                  fill="rgba(124,58,237,0.08)"
                  stroke="#7c3aed"
                  strokeWidth={2.5}
                  strokeDasharray="10 6"
                />
              ))}
              {layers.proposed.polylines.map((d, i) => (
                <path key={`pl${i}`} d={d} fill="none" stroke="#7c3aed" strokeWidth={2.5} strokeDasharray="10 6" />
              ))}
              {layers.proposed.points.map((p, i) => {
                const pos = project(p[0], p[1], bounds);
                return <circle key={`pp${i}`} cx={pos.x} cy={pos.y} r={5} fill="#7c3aed" />;
              })}
              {layers.proposed.label && (
                <text
                  x={layers.proposed.label.x}
                  y={layers.proposed.label.y}
                  textAnchor="middle"
                  className="gis-label gis-label-proposed"
                >
                  {layers.proposed.label.text}
                </text>
              )}
            </>
          )}

          {layers.labels.map((l, i) => (
            <text key={`l${i}`} x={l.x} y={l.y} textAnchor="middle" className="gis-label">
              {l.text}
            </text>
          ))}

          {probePos && (
            <>
              <circle cx={probePos.x} cy={probePos.y} r={10} fill="rgba(220,38,38,0.25)" />
              <circle cx={probePos.x} cy={probePos.y} r={4} fill="#dc2626" stroke="#ffffff" strokeWidth={1.5} />
            </>
          )}

          {selectedPos && (
            <g className="gis-selected-location">
              {selectedAccuracyR > 0 && (
                <circle
                  cx={selectedPos.x}
                  cy={selectedPos.y}
                  r={selectedAccuracyR}
                  fill="rgba(37,99,235,0.12)"
                  stroke="rgba(37,99,235,0.5)"
                  strokeWidth={1.5}
                  strokeDasharray="4 3"
                />
              )}
              <circle cx={selectedPos.x} cy={selectedPos.y} r={11} fill="rgba(29,78,216,0.25)" />
              <circle cx={selectedPos.x} cy={selectedPos.y} r={5} fill="#1d4ed8" stroke="#ffffff" strokeWidth={2} />
            </g>
          )}
        </g>

        {activeVersionLabels.length > 0 && (
          <text x={VIEW_W - PAD} y={PAD - 8} textAnchor="end" className="gis-version">
            {activeVersionLabels.join(" · ")}
          </text>
        )}
      </svg>
    </div>
  );
}