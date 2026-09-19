import { useEffect, useMemo, useRef, useState } from "react";
import {
  AttributionControl,
  Circle,
  GeoJSON,
  MapContainer,
  Marker,
  TileLayer,
  Tooltip,
  ZoomControl,
  useMap,
  useMapEvents,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import type {
  AreaSummary,
  GeoJsonGeometry,
  JurisdictionSummary,
  RoadSummary,
} from "../../api/gisTypes";
import type { SelectedLocation } from "../../lib/geolocation";

const MYSURU_CENTER: [number, number] = [12.2958, 76.6394];
const INITIAL_ZOOM = 13;
const MAX_ZOOM = 19;

/** Curated Mysuru civic viewport (same region the SVG map projected). */
const VIEW_BOUNDS = {
  minLat: 12.1,
  maxLat: 12.45,
  minLng: 76.4,
  maxLng: 76.92,
};

/** Leave a little slack so users can see the dataset's edges. */
const MAP_BOUNDS: [[number, number], [number, number]] = [
  [VIEW_BOUNDS.minLat - 0.1, VIEW_BOUNDS.minLng - 0.1],
  [VIEW_BOUNDS.maxLat + 0.1, VIEW_BOUNDS.maxLng + 0.1],
];

const OSM_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const OSM_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

const SELECTED_ICON = L.divIcon({
  className: "civic-marker",
  html: '<div class="civic-marker-pin civic-marker-pin-selected"></div>',
  iconSize: [22, 30],
  iconAnchor: [11, 30],
  popupAnchor: [0, -30],
});

const PROBE_ICON = L.divIcon({
  className: "civic-marker",
  html: '<div class="civic-marker-pin civic-marker-pin-probe"></div>',
  iconSize: [22, 30],
  iconAnchor: [11, 30],
  popupAnchor: [0, -30],
});

function toFeature(
  geometry: GeoJsonGeometry,
  properties: Record<string, string>,
): Feature | null {
  if (!geometry || !geometry.type || !geometry.coordinates) return null;
  return {
    type: "Feature",
    properties,
    geometry: geometry as Geometry,
  } as Feature;
}

function collectLatLngs(coords: unknown, out: [number, number][]): void {
  if (!Array.isArray(coords)) return;
  if (coords.length === 2 && typeof coords[0] === "number" && typeof coords[1] === "number") {
    out.push([coords[1], coords[0]]);
    return;
  }
  for (const entry of coords) collectLatLngs(entry, out);
}

function featureCollection(features: Feature[]): FeatureCollection | null {
  if (features.length === 0) return null;
  return { type: "FeatureCollection", features };
}

function FocusController({ focus }: { focus: { lat: number; lng: number } | null }) {
  const map = useMap();
  const lastRef = useRef<string | null>(null);

  useEffect(() => {
    if (!focus) return;
    const lat = clamp(focus.lat, VIEW_BOUNDS.minLat, VIEW_BOUNDS.maxLat);
    const lng = clamp(focus.lng, VIEW_BOUNDS.minLng, VIEW_BOUNDS.maxLng);
    const key = `${lat.toFixed(5)},${lng.toFixed(5)}`;
    if (lastRef.current === key) return;
    lastRef.current = key;
    map.setView([lat, lng], Math.max(map.getZoom(), 15), { animate: true });
  }, [focus, map]);

  return null;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function FitBounds({ bounds }: { bounds: L.LatLngBounds | null }) {
  const map = useMap();
  const seenRef = useRef<string | null>(null);

  useEffect(() => {
    if (!bounds) return;
    const bbox = bounds.toBBoxString();
    if (seenRef.current === bbox) return;
    seenRef.current = bbox;
    map.fitBounds(bounds, { padding: [24, 24], maxZoom: 16 });
  }, [bounds, map]);

  return null;
}

interface OverlayProps {
  jurisdictions: JurisdictionSummary[];
  areas: AreaSummary[];
  roads: RoadSummary[];
  highlightCode: string | null;
}

function JurisdictionOverlays({ jurisdictions, areas, roads, highlightCode }: OverlayProps) {
  const { jurisdictionFeatures, areaFeatures, roadFeatures, coordinates } = useMemo(() => {
    const jFeatures: Feature[] = [];
    const aFeatures: Feature[] = [];
    const rFeatures: Feature[] = [];
    const coordinates: [number, number][] = [];

    for (const j of jurisdictions) {
      const feature = toFeature(j.geometry_geojson ?? ({} as GeoJsonGeometry), {
        code: j.code,
        name: j.name,
        kind: j.kind,
      });
      if (feature) {
        jFeatures.push(feature);
        collectLatLngs(j.geometry_geojson?.coordinates, coordinates);
      }
    }
    for (const a of areas) {
      const feature = toFeature(a.geometry_geojson ?? ({} as GeoJsonGeometry), {
        code: a.code,
        name: a.name,
        kind: "AREA",
      });
      if (feature) {
        aFeatures.push(feature);
        collectLatLngs(a.geometry_geojson?.coordinates, coordinates);
      }
    }
    for (const r of roads) {
      const feature = toFeature(r.geometry_geojson ?? ({} as GeoJsonGeometry), {
        code: r.code,
        name: r.name,
        kind: "ROAD",
      });
      if (feature) {
        rFeatures.push(feature);
        collectLatLngs(r.geometry_geojson?.coordinates, coordinates);
      }
    }
    return {
      jurisdictionFeatures: jFeatures,
      areaFeatures: aFeatures,
      roadFeatures: rFeatures,
      coordinates,
    };
  }, [jurisdictions, areas, roads]);

  const styleByKind = useMemo(
    () => (feature?: Feature) => {
      const kind = feature?.properties?.kind;
      const code = feature?.properties?.code;
      const highlight = highlightCode != null && code === highlightCode;
      switch (kind) {
        case "WARD":
          return {
            color: highlight ? "#111827" : "#0f766e",
            weight: highlight ? 3 : 2,
            opacity: highlight ? 1 : 0.8,
            fillColor: "#ccfbf1",
            fillOpacity: 0.22,
          } as L.PathOptions;
        case "SPECIAL_CORRIDOR":
          return {
            color: "#b45309",
            weight: 2,
            dashArray: "6 4",
            fillColor: "#f59e0b",
            fillOpacity: 0.08,
          } as L.PathOptions;
        case "HERITAGE_ZONE":
          return {
            color: "#d97706",
            weight: 2,
            fillColor: "#d97706",
            fillOpacity: 0.12,
          } as L.PathOptions;
        case "ROAD":
          return {
            color: "#15803d",
            weight: 3,
            opacity: 0.9,
            fillOpacity: 0,
          } as L.PathOptions;
        case "AREA":
          return {
            color: "#4f46e5",
            weight: 1.5,
            fillColor: "#4f46e5",
            fillOpacity: 0.06,
          } as L.PathOptions;
        default:
          return {
            color: "#94a3b8",
            weight: 1.5,
            fillColor: "#e2e8f0",
            fillOpacity: 0.15,
          } as L.PathOptions;
      }
    },
    [highlightCode],
  );

  const onEachFeature = useMemo(
    () => (feature: Feature, layer: L.Layer) => {
      if (feature.properties?.code && feature.properties?.name) {
        layer.bindTooltip(`${feature.properties.code} · ${feature.properties.name}`, {
          sticky: true,
        });
      }
    },
    [],
  );

  const jurisdictionCollection = useMemo(
    () => featureCollection(jurisdictionFeatures),
    [jurisdictionFeatures],
  );
  const areaCollection = useMemo(() => featureCollection(areaFeatures), [areaFeatures]);
  const roadCollection = useMemo(() => featureCollection(roadFeatures), [roadFeatures]);
  const bounds = useMemo(
    () => (coordinates.length >= 2 ? L.latLngBounds(coordinates) : null),
    [coordinates],
  );

  return (
    <>
      <FitBounds bounds={bounds} />
      {jurisdictionCollection && (
        <GeoJSON
          key="jurisdictions"
          data={jurisdictionCollection}
          style={styleByKind}
          onEachFeature={onEachFeature}
        />
      )}
      {areaCollection && (
        <GeoJSON key="areas" data={areaCollection} style={styleByKind} onEachFeature={onEachFeature} />
      )}
      {roadCollection && (
        <GeoJSON key="roads" data={roadCollection} style={styleByKind} onEachFeature={onEachFeature} />
      )}
    </>
  );
}

function MapClickHandler({ onSelect }: { onSelect: (lat: number, lng: number) => void }) {
  useMapEvents({
    click: (event: L.LeafletMouseEvent) => {
      onSelect(event.latlng.lat, event.latlng.lng);
    },
  });
  return null;
}

export interface CivicMapProps {
  jurisdictions: JurisdictionSummary[];
  areas: AreaSummary[];
  roads: RoadSummary[];
  selectedLocation: SelectedLocation | null;
  focusLocation: { lat: number; lng: number } | null;
  probe: { lat: number; lng: number } | null;
  highlightCode: string | null;
  activeVersionLabels: string[];
  onSelect: (lat: number, lng: number) => void;
}

export function CivicMap({
  jurisdictions,
  areas,
  roads,
  selectedLocation,
  focusLocation,
  probe,
  highlightCode,
  activeVersionLabels,
  onSelect,
}: CivicMapProps) {
  const [tileFailed, setTileFailed] = useState(false);
  const tileErrors = useRef(0);

  const handleTileError = useMemo(() => () => {
    tileErrors.current += 1;
    if (tileErrors.current >= 5) setTileFailed(true);
  }, []);

  const handleTileLoad = useMemo(() => () => {
    if (tileFailed) setTileFailed(false);
    tileErrors.current = 0;
  }, [tileFailed]);

  return (
    <div className="civic-map-outer">
      <div className="civic-map-wrap">
        <MapContainer
          center={MYSURU_CENTER}
          zoom={INITIAL_ZOOM}
          maxZoom={MAX_ZOOM}
          maxBounds={MAP_BOUNDS}
          maxBoundsViscosity={1}
          scrollWheelZoom
          zoomControl={false}
          attributionControl={false}
          className="civic-map"
        >
          <MapClickHandler onSelect={onSelect} />
          <TileLayer
            url={OSM_TILE_URL}
            attribution={OSM_ATTRIBUTION}
            maxZoom={MAX_ZOOM}
            eventHandlers={{ tileerror: handleTileError, tileload: handleTileLoad }}
          />
          <ZoomControl position="topleft" />
          <AttributionControl position="bottomright" prefix={false} />

          <JurisdictionOverlays
            jurisdictions={jurisdictions}
            areas={areas}
            roads={roads}
            highlightCode={highlightCode}
          />

          {selectedLocation && selectedLocation.source === "gps" && selectedLocation.accuracy != null && (
            <Circle
              center={[selectedLocation.latitude, selectedLocation.longitude]}
              radius={selectedLocation.accuracy}
              pathOptions={{
                color: "#2563eb",
                weight: 1.5,
                dashArray: "4 3",
                fillColor: "#3b82f6",
                fillOpacity: 0.12,
              }}
            />
          )}

          {selectedLocation && (
            <Marker
              position={[selectedLocation.latitude, selectedLocation.longitude]}
              icon={SELECTED_ICON}
            />
          )}

          {probe && (
            <Marker position={[probe.lat, probe.lng]} icon={PROBE_ICON}>
              <Tooltip direction="top" offset={[0, -22]} opacity={0.95}>
                Routed point
              </Tooltip>
            </Marker>
          )}

          <FocusController focus={focusLocation} />
        </MapContainer>

        {tileFailed && (
          <div className="civic-map-notice" role="status">
            Street tiles are unavailable (offline?). The civic jurisdiction overlay is still shown.
          </div>
        )}
      </div>

      <CivicLegend activeVersionLabels={activeVersionLabels} />
    </div>
  );
}

function CivicLegend({ activeVersionLabels }: { activeVersionLabels: string[] }) {
  return (
    <div className="gis-legend civic-legend" role="list" aria-label="CIVIC JURISDICTION map legend">
      <div className="civic-legend-title">
        CIVIC JURISDICTION
        {activeVersionLabels.length > 0 && (
          <span className="gis-version civic-legend-versions">
            {activeVersionLabels.join(" · ")}
          </span>
        )}
      </div>
      <span className="gis-legend-item" role="listitem">
        <span className="gis-legend-swatch gis-legend-swatch-ward" aria-hidden="true" />
        Ward boundary
      </span>
      <span className="gis-legend-item" role="listitem">
        <span className="gis-legend-swatch gis-legend-swatch-heritage" aria-hidden="true" />
        Heritage area
      </span>
      <span className="gis-legend-item" role="listitem">
        <span className="gis-legend-swatch gis-legend-swatch-corridor" aria-hidden="true" />
        Road / corridor
      </span>
      <span className="gis-legend-item" role="listitem">
        <span className="gis-legend-swatch gis-legend-swatch-area" aria-hidden="true" />
        Jurisdiction area
      </span>
      <span className="gis-legend-item" role="listitem">
        <span className="gis-legend-swatch gis-legend-swatch-selected" aria-hidden="true" />
        Selected location
      </span>
      <span className="gis-legend-item" role="listitem">
        <span className="gis-legend-swatch gis-legend-swatch-gps" aria-hidden="true" />
        Your location (with GPS range)
      </span>
    </div>
  );
}