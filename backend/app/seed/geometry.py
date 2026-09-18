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
        (76.6*2 + 0.0328, 12.335),
        (76.64, 12.335),
        (76.64 + 0.0142, 12.335),
    ]
)

# ---------------------------------------------------------------------------
# Heritage precinct + PROPOSED overlay (P3 what-if simulator)
# ---------------------------------------------------------------------------
# The live heritage precinct watches the seeded ``HERITAGE_ZONE`` (see
# ``app.seed.seed_runner._seed_jurisdictions``). P3 what-if scenarios resolve
# against a *proposed* expanded preserve — ``HERITAGE_ZONE_EXPANDED`` — which
# is deterministic, isolated from the live ``jurisdictions`` table (no row is
# ever created or mutated) and used only to compute proposed deltas.
HERITAGE_ZONE = Polygon(
    [
        (76.62, 12.305),
        (76.65, 12.305),
        (76.65, 12.32),
        (76.62, 12.32),
    ]
)

# Deterministic expansion of HERITAGE_ZONE used by what-if simulation. Same
# center (76.635, 12.3125); each edge pushed outward by a fixed quarter degree
# cell so the demo "proposed heritage preserve" is visually distinct from the
# live zone yet derived purely from it.
HERITAGE_ZONE_EXPANDED = Polygon(
    [
        (76.615, 12.30),
        (76.655, 12.30),
        (76.655, 12.325),
        (76.615, 12.325),
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
        """Derive the ``(row, col)``-addressed view of the underlying ``grid``.

        The flat ``grid`` is keyed ``row * n_cols + col``; this read-only view
        restores the 2-D ``(row, col)`` addressing that ``seed_runner`` uses to
        enumerate cells in deterministic sorted order, without mutating the
        stored ``grid`` contract.
        """
        return {
            (row, col): self.grid[row * self.n_cols + col]
            for row in range(self.n_rows)
            for col in range(self.n_cols)
        }

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
    interior point of the first V1 cell. The two demo mosaics are geometrically
    congruent (they share the same bbox fractions), so this never loops without
    bound and is fully reproducible for a given seeded ``rng``.
    """
    ordered_v2 = sorted(cells_v2.items())
    for (row1, col1), cell1 in sorted(cells_v1.items()):
        minx, miny, maxx, maxy = cell1.bounds
        for _ in range(8):
            px = minx + (maxx - minx) * rng.random()
            py = miny + (maxy - miny) * rng.random()
            probe = Point(px, py)
            if not cell1.covers(probe):
                continue
            for (row2, col2), cell2 in ordered_v2:
                if cell2.covers(probe) and (row2, col2) != (row1, col1):
                    return (float(px), float(py))
            break
    (_, _), fallback_cell = sorted(cells_v1.items())[0]
    minx, miny, maxx, maxy = fallback_cell.bounds
    while True:
        px = minx + (maxx - minx) * rng.random()
        py = miny + (maxy - miny) * rng.random()
        if fallback_cell.covers(Point(px, py)):
            return (float(px), float(py))


# ---------------------------------------------------------------------------
# HERITAGE ZONE + PROPOSED EXPANSION (P3 what-if simulator)
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


# ---------------------------------------------------------------------------
# Deterministic ward-demo mosaic bounds (SYNTHETIC DEMO DATA)
#
# The P1/P3 seed mosaic needs a stable outer rectangle to slice into a 3x3
# ward grid. These four floats are pure demo bounds: they enclose both
# ``NH_CORRIDOR`` and ``HERITAGE_ZONE``/``HERITAGE_ZONE_EXPANDED`` above and
# are never persisted as a real spatial boundary anywhere.
# ---------------------------------------------------------------------------
WARD_MINX = 76.59
WARD_MINY = 12.27
WARD_MAXX = 76.68
WARD_MAXY = 12.34
