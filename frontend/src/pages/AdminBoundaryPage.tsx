import { useEffect, useMemo, useState } from "react";
import { ApiError, fetchAreas, fetchJurisdictions, fetchRoads } from "../api";
import type {
  AreaSummary,
  JurisdictionSummary,
  RoadSummary,
} from "../api/gisTypes";
import { JurisdictionMap } from "../components/map/JurisdictionMap";
import { MapLegend } from "../components/map/MapLegend";

const DATE_PRESETS = [
  { label: "V1 ▸ V2", earlier: "2023-01-01", later: "2024-06-01" },
  { label: "V1 ▸ current", earlier: "2023-01-01", later: "2026-09-18" },
  { label: "V2 ▸ current", earlier: "2024-06-01", later: "2026-09-18" },
];

type LoadState =
  | { kind: "loading" }
  | { kind: "ok" }
  | { kind: "error"; message: string };

interface CompareRow {
  code: string;
  name: string;
  kind: string;
  authority: string;
  earlier: JurisdictionSummary | null;
  later: JurisdictionSummary | null;
  boundaryChange: boolean;
}

function cellFrom(j: JurisdictionSummary | null) {
  if (!j) return null;
  return {
    version: j.version_code,
    status: j.version_status,
    effective_from: j.effective_from,
    effective_to: j.effective_to,
    superseded_by: j.superseded_by_code,
  };
}

function windowText(from: string, to: string | null) {
  return `${from} → ${to ?? "open"}`;
}

export default function AdminBoundaryPage() {
  const [earlierDate, setEarlierDate] = useState("2023-01-01");
  const [laterDate, setLaterDate] = useState("2026-09-18");
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [earlierList, setEarlierList] = useState<JurisdictionSummary[]>([]);
  const [laterList, setLaterList] = useState<JurisdictionSummary[]>([]);
  const [areas, setAreas] = useState<AreaSummary[]>([]);
  const [roads, setRoads] = useState<RoadSummary[]>([]);
  const [mapSnapshot, setMapSnapshot] = useState<"earlier" | "later">("later");
  const [selectedCode, setSelectedCode] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setState({ kind: "loading" });
    Promise.all([
      fetchAreas(),
      fetchRoads(),
      fetchJurisdictions({ date: earlierDate, includeGeometry: true }),
      fetchJurisdictions({ date: laterDate, includeGeometry: true }),
    ])
      .then(([areasRes, roadsRes, earlierRes, laterRes]) => {
        if (cancelled) return;
        setAreas(areasRes.areas);
        setRoads(roadsRes.roads);
        setEarlierList(earlierRes.jurisdictions);
        setLaterList(laterRes.jurisdictions);
        setSelectedCode(null);
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
  }, [earlierDate, laterDate]);

  const rows = useMemo<CompareRow[]>(() => {
    const byCode = new Map<string, CompareRow>();
    const add = (j: JurisdictionSummary, side: "earlier" | "later") => {
      const row = byCode.get(j.code) ?? {
        code: j.code,
        name: j.name,
        kind: j.kind,
        authority: j.authority_code,
        earlier: null,
        later: null,
        boundaryChange: false,
      };
      row[side] = j;
      byCode.set(j.code, row);
    };
    earlierList.forEach((j) => add(j, "earlier"));
    laterList.forEach((j) => add(j, "later"));
    const rows = Array.from(byCode.values());
    for (const row of rows) {
      row.boundaryChange =
        (row.earlier != null && row.later != null && row.earlier.version_code !== row.later.version_code) ||
        Boolean(row.earlier?.superseded_by_code) ||
        Boolean(row.later?.superseded_by_code) ||
        (row.earlier != null && row.later == null) ||
        (row.earlier == null && row.later != null);
    }
    return rows.sort((a, b) => a.kind.localeCompare(b.kind) || a.code.localeCompare(b.code));
  }, [earlierList, laterList]);

  const mapData = mapSnapshot === "earlier" ? earlierList : laterList;
  const activeVersionLabels = useMemo(
    () => Array.from(new Set(mapData.map((j) => j.version_code).filter(Boolean))) as string[],
    [mapData],
  );
  const changeCount = rows.filter((r) => r.boundaryChange).length;

  return (
    <section className="page">
      <header className="page-header">
        <h1>Admin Boundaries</h1>
        <p>
          Read-only boundary administration view — inspect jurisdiction versions, their
          effective windows and boundary changes across time. This prototype never mutates
          live jurisdiction records: no add, edit or delete endpoints are exposed.
        </p>
        <span className="implemented-badge">IMPLEMENTED</span>{" "}
        <span className="muted-tag">READ-ONLY</span>
      </header>

      <div className="replay-form admin-compare-form">
        <div className="gis-toolbar-item">
          <label htmlFor="snapshot-earlier">Earlier snapshot (A)</label>
          <input
            id="snapshot-earlier"
            type="date"
            min="2020-01-01"
            max="2026-12-31"
            value={earlierDate}
            onChange={(event) => setEarlierDate(event.target.value)}
          />
        </div>
        <div className="gis-toolbar-item">
          <label htmlFor="snapshot-later">Later snapshot (B)</label>
          <input
            id="snapshot-later"
            type="date"
            min="2020-01-01"
            max="2026-12-31"
            value={laterDate}
            onChange={(event) => setLaterDate(event.target.value)}
          />
        </div>
        <div className="gis-quick">
          {DATE_PRESETS.map((preset) => (
            <button
              key={preset.label}
              className="chip"
              onClick={() => {
                setEarlierDate(preset.earlier);
                setLaterDate(preset.later);
              }}
            >
              {preset.label}
            </button>
          ))}
        </div>
        <p className="admin-compare-note">
          Comparing the version in force on two dates reveals each jurisdiction's version
          history and boundary changes. The list API returns the version active on each
          requested date — nothing here is written back.
        </p>
      </div>

      {state.kind === "loading" && <p className="muted">Loading boundary snapshots…</p>}
      {state.kind === "error" && <p className="error-text">{state.message}</p>}

      {state.kind === "ok" && (
        <>
          <div className="admin-summary muted">
            {rows.length} jurisdiction records · {earlierList.length} in force on{" "}
            {earlierDate} · {laterList.length} in force on {laterDate} · {changeCount}{" "}
            boundary change{changeCount === 1 ? "" : "s"} detected.
          </div>

          <div className="gis-layout">
            <div className="card gis-map-card">
              <h3>Boundary snapshot · {mapSnapshot === "earlier" ? "A" : "B"} ({mapSnapshot === "earlier" ? earlierDate : laterDate})</h3>
              <JurisdictionMap
                jurisdictions={mapData}
                areas={areas}
                roads={roads}
                probe={null}
                highlightCode={selectedCode}
                activeVersionLabels={activeVersionLabels}
                onSelect={() => undefined}
              />
              <MapLegend />
              <p className="muted gis-click-hint">
                Click a row to highlight its boundary on the map. Snapshot{" "}
                <button className="link-button" onClick={() => setMapSnapshot("earlier")}>
                  A
                </button>{" "}
                /{" "}
                <button className="link-button" onClick={() => setMapSnapshot("later")}>
                  B
                </button>{" "}
                switches which in-force version is drawn.
              </p>
            </div>

            <div className="card gis-result-card">
              <h3>Version comparison</h3>
              {rows.length === 0 && <p className="muted">No jurisdiction records found.</p>}
              {rows.length > 0 && (
                <div className="admin-table-wrap">
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Jurisdiction</th>
                        <th>Kind</th>
                        <th>Snapshot A · {earlierDate}</th>
                        <th>Snapshot B · {laterDate}</th>
                        <th>Boundary change</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row) => {
                        const a = cellFrom(row.earlier);
                        const b = cellFrom(row.later);
                        return (
                          <tr
                            key={row.code}
                            className={selectedCode === row.code ? "selected" : ""}
                            onClick={() => {
                              setSelectedCode(row.code);
                              if (row.later) setMapSnapshot("later");
                              else setMapSnapshot("earlier");
                            }}
                          >
                            <td>
                              <span className="admin-juris-code">{row.code}</span>
                              <span className="admin-juris-name">{row.name}</span>
                            </td>
                            <td><span className="muted-tag">{row.kind}</span></td>
                            <td>{a ? <VersionCell v={a} /> : <span className="muted">not in force</span>}</td>
                            <td>{b ? <VersionCell v={b} /> : <span className="muted">not in force</span>}</td>
                            <td>
                              {row.boundaryChange ? (
                                <span className="boundary-change-badge">● BOUNDARY CHANGE</span>
                              ) : (
                                <span className="muted">—</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}

function VersionCell({ v }: { v: { version: string; status: string; effective_from: string; effective_to: string | null; superseded_by: string | null } }) {
  return (
    <div className="admin-version-cell">
      <span className="admin-version-code">{v.version} · {v.status}</span>
      <span className="admin-version-window">{windowText(v.effective_from, v.effective_to)}</span>
      {v.superseded_by && <span className="admin-superseded">superseded by {v.superseded_by}</span>}
    </div>
  );
}