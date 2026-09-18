import type { CSSProperties } from "react";

interface LegendItem {
  label: string;
  style: CSSProperties;
}

const ITEMS: LegendItem[] = [
  {
    label: "Ward",
    style: { background: "#ccfbf1", border: "2px solid #0f766e" },
  },
  {
    label: "Special corridor",
    style: { background: "rgba(245,158,11,0.10)", border: "2px dashed #b45309" },
  },
  {
    label: "Heritage zone",
    style: { background: "rgba(217,119,6,0.12)", border: "2px solid #d97706" },
  },
];

export function MapLegend({ showProposed = false }: { showProposed?: boolean }) {
  const items = showProposed
    ? [
        ...ITEMS,
        {
          label: "Proposed geometry",
          style: { background: "rgba(124,58,237,0.08)", border: "2px dashed #7c3aed" },
        },
      ]
    : ITEMS;

  return (
    <div className="gis-legend" role="list" aria-label="Map legend">
      {items.map((item) => (
        <span key={item.label} className="gis-legend-item" role="listitem">
          <span className="gis-legend-swatch" style={item.style} aria-hidden="true" />
          {item.label}
        </span>
      ))}
    </div>
  );
}