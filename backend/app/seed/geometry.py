"""Deterministic demo geometry providers for the temporal civic twin (P0/P1).

All coordinates in this module are SYNTHETIC DEMO DATA. They approximate the
real scale and shape of Mysuru, India, so the demo looks believable, but they
are deliberately fictional and must never be treated as real boundaries.
"""
from __future__ import annotations

from dataclasses import dataclass
import random

from shapely.geometry import Point, Polygon
NH_CORRIDOR = Polygon(
    [
        (76.56, 12.335),
        (76.72, 12.335),
        (76.72, 12.339),
        (76.56, 12.339),
    ]
)

# ---------------------------------------------------------------------------
# Heritage precinct + PROPOSED overlay (P3 what-if simulator)
#
# ``HERITAGE_ZONE`` is the live heritage precinct boundary seeded in
# ``seed_runner._seed_jurisdictions``. ``HERITAGE_ZONE_EXPANDED`` is the
# deterministic *proposed* overlay boundary the P3 what-if simulator resolves
# against; it is deliberately read-only and is never written to the live
# ``jurisdictions`` table.
# ---------------------------------------------------------------------------
HERITAGE_ZONE = Polygon(
    [(76.6328, 12.298), (76.6542, 12.298), (76.6542, 12.3082), (76.6328, 12.3082)]
)


HERITAGE_ZONE_EXPANDED = Polygon(
    [
        (76.629, 12.295), (76.658, 12.295), (76.658, 12.311),
        (76.629, 12.311),
    ]
)


@dataclass(frozen=True)
class Mosaic:
    """A deterministic mosaic of cells covering the ward bbox on a grid."""

    n_rows: int
    n_cols: int
    grid: dict[int, Polygon]

    @property
    def cells(self) -> dict[tuple[int, int], Polygon]:
        """Address the mosaic by grid coordinate, ``{(row, col): cell}``.

        Derived deterministically from the flat ``grid`` (keyed
        ``row * n_cols + col``) so the seed layer can enumerate cells in
        ``(row, col)`` order without changing the stored ``grid`` contract.
        """
        return {
            (row, col): self.grid[row * self.n_cols + col]
            for row in range(self.n_rows)
            for col in range(self.n_cols)
        }


def build_mosaic(
    minx: float, miny: float, maxx: float, maxy: float,
    n_rows: int, n_cols: int, seed: int,
) -> Mosaic:
    """Build the grid the seed uses to flip coordinates in a deterministic way"""
    rng = random.Random(seed)
    cells: dict[int, Polygon] = {}
    for row in range(n_rows):
        for col in range(n_cols):
            x0 = minx + (maxx - minx) * col / n_cols
            y0 = miny + (maxy - miny) * row / n_rows
            x1 = minx + (maxx - minx) * (col + 1) / n_cols
            y1 = miny + (maxy - miny) * (row + 1) / n_rows
            cells[row * n_cols + col] = Polygon(
                [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            )
    return Mosaic(n_rows=n_rows, n_cols=n_cols, grid=cells)


def _cell_key(cells: dict[int, Polygon], point: Point) -> int | None:
    for key, cell in cells.items():
        if cell.covers(point):
            return key
    return None


def find_flip_point(polygon: Polygon, seed: int = 7) -> Point:
    """Deterministically pick a point inside ``polygon`` and at least partially
    on the NO-JURISDICTION side of the built mosaic, for demo complaints."""
    minx, miny, maxx, maxy = polygon.bounds
    rng = random.Random(seed)
    while True:
        px = minx + (maxx - minx) * rng.random()
        py = miny + (maxy - miny) * rng.random()
        point = Point(px, py)
        if polygon.covers(point):
            return point


def find_flip_point_between(
    cells_v1: dict[tuple[int, int], Polygon],
    cells_v2: dict[tuple[int, int], Polygon],
    rng: random.Random,
) -> tuple[float, float]:
    """Deterministically return a ``(lon, lat)`` whose covering ``(row, col)``
    cell differs between the V1 and V2 mosaics, if one exists; otherwise an
    interior point of the first V1 cell. Probing is bounded (64 draws per cell
    against the sorted V2 cells) and falls back to a seeded interior point
    of the first V1 cell, so it always terminates and is fully reproducible for
    a given seeded ``rng``.
    """
    ordered_v2 = sorted(cells_v2.items())
    for (row1, col1), cell1 in sorted(cells_v1.items()):
        minx, miny, maxx, maxy = cell1.bounds
        for _ in range(64):
            px = minx + (maxx - minx) * rng.random()
            py = miny + (maxy - miny) * rng.random()
            probe = Point(px, py)
            if not cell1.covers(probe):
                continue
            for (row2, col2), cell2 in ordered_v2:
                if cell2.covers(probe) and (row2, col2) != (row1, col1):
                    return (float(px), float(py))
    (_, _), fallback_cell = sorted(cells_v1.items())[0]
    minx, miny, maxx, maxy = fallback_cell.bounds
    while True:
        px = minx + (maxx - minx) * rng.random()
        py = miny + (maxy - miny) * rng.random()
        if fallback_cell.covers(Point(px, py)):
            return (float(px), float(py))


# ---------------------------------------------------------------------------
# Deterministic ward-demo mosaic bounds (SYNTHETIC DEMO DATA)
#
# The P1/P3 seed mosaic needs a stable outer rectangle to slice into a 3x3
# ward grid. These four floats are pure demo bounds: they enclose both
# ``NH_CORRIDOR`` and ``HERITAGE_ZONE``/``HERITAGE_ZONE_EXPANDED`` above and
# are never persisted as a real spatial boundary anywhere.
# ---------------------------------------------------------------------------
WARD_MINX = 76.59
WARD_MINY = 12.22
WARD_MAXX = 76.68
WARD_MAXY = 12.335

# The two demo delimitations are sliced differently on purpose:
# * V1 (DELIM-2020) is a plain uniform 3x3 grid over the ward bbox.
# * V2 (DELIM-2024) keeps the west column's rows anchored at 12.22 but lifts
#   the east columns' south edge to 12.27 (a staircase): the 12.22-12.27 band
#   east of the west column falls between cells, which is exactly the
#   deterministic no-jurisdiction pocket (C-1004) the demo documents. The
#   shifted column cuts also re-slice the grid so some coordinates change ward
#   between the versions - the seeded "flip point" premise.
WARD_V1_COL_CUTS = (76.59, 76.62, 76.65, 76.68)
WARD_V1_ROW_CUTS = (12.22, 12.293333333333333, 12.316666666666666, 12.335)
WARD_V2_COL_CUTS = (76.59, 76.617, 76.649, 76.68)
WARD_V2_WEST_ROW_CUTS = (12.22, 12.293333333333333, 12.316666666666666, 12.335)
WARD_V2_EAST_ROW_CUTS = (12.27, 12.293333333333333, 12.316666666666666, 12.335)


def build_ward_mosaic(
    col_cuts: tuple[float, ...], row_cuts: dict[int, tuple[float, ...]]
) -> Mosaic:
    """Build a 3x3 ward mosaic with per-column row cuts.

    ``row_cuts`` maps each column index to the row-cut tuple that slices that
    column's cells. Columns may therefore start their rows at different south
    edges (the V2 staircase), while cell addressing stays ``(row, col)``.
    """
    n_cols = len(col_cuts) - 1
    n_rows = len(next(iter(row_cuts.values()))) - 1
    cells: dict[int, Polygon] = {}
    for col in range(n_cols):
        cuts = row_cuts[col]
        for row in range(n_rows):
            cells[row * n_cols + col] = Polygon(
                [
                    (col_cuts[col], cuts[row]),
                    (col_cuts[col + 1], cuts[row]),
                    (col_cuts[col + 1], cuts[row + 1]),
                    (col_cuts[col], cuts[row + 1]),
                ]
            )
    return Mosaic(n_rows=n_rows, n_cols=n_cols, grid=cells)


def build_v1_ward_mosaic() -> Mosaic:
    """Uniform grid for the DELIM-2020 ward layout."""
    return build_ward_mosaic(
        WARD_V1_COL_CUTS,
        {0: WARD_V1_ROW_CUTS, 1: WARD_V1_ROW_CUTS, 2: WARD_V1_ROW_CUTS},
    )


def build_v2_ward_mosaic() -> Mosaic:
    """Staircase grid for the DELIM-2024 ward layout (east columns lifted)."""
    return build_ward_mosaic(
        WARD_V2_COL_CUTS,
        {0: WARD_V2_WEST_ROW_CUTS, 1: WARD_V2_EAST_ROW_CUTS, 2: WARD_V2_EAST_ROW_CUTS},
    )
