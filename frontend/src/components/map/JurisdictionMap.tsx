import { useMemo, useRef } from "react";
import type { MouseEvent } from "react";
import type {
  GeoJsonGeometry,
  JurisdictionSummary,
  Position,
} from "../../api/gisTypes";

const VIEW_W = 960;
const VIEW_H = 600;
const PAD = 48;

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
}: MapProps) {
  const svgRef = useRef<SVGSVGElement | null>(null);

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

  const handleClick = (event: MouseEvent<SVGSVGElement>) => {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const vx = ((event.clientX - rect.left) / rect.width) * VIEW_W;
    const vy = ((event.clientY - rect.top) / rect.height) * VIEW_H;
    const lon = bounds.minLon + ((vx - PAD) / (VIEW_W - 2 * PAD)) * (bounds.maxLon - bounds.minLon);
    const lat = bounds.maxLat - ((vy - PAD) / (VIEW_H - 2 * PAD)) * (bounds.maxLat - bounds.minLat);
    const clampedLat = Math.min(90, Math.max(-90, lat));
    const clampedLon = Math.min(180, Math.max(-180, lon));
    onSelect(clampedLat, clampedLon);
  };

  const probePos = probe ? project(probe.lng, probe.lat, bounds) : null;

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
      className="gis-map"
      onClick={handleClick}
      role="img"
      aria-label="Jurisdiction map"
    >
      <rect x="0" y="0" width={VIEW_W} height={VIEW_H} fill="#eaf3ee" />

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

      {activeVersionLabels.length > 0 && (
        <text x={VIEW_W - PAD} y={PAD - 8} textAnchor="end" className="gis-version">
          {activeVersionLabels.join(" · ")}
        </text>
      )}
    </svg>
  );
}