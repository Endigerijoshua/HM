"""Deterministic synthetic Mysuru-style geometry generator.

All coordinates in this module are SYNTHETIC DEMO DATA. They approximate the
shape and scale of Mysuru so the demo is visually believable, but they are
NOT official boundaries and must never be presented as such.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from shapely.geometry import Point, Polygon

# Synthetic bounding box for the demo region (Mysuru-scale).
WARD_MINX, WARD_MINY, WARD_MAXX, WARD_MAXY = 76.56, 12.22, 76.72, 12.335

# Synthetic NH corridor band directly north of the ward mosaic.
NH_CORRIDOR = Polygon(
    [
        (76.56, 12.335),
        (76.72, 12.335),
        (76.72, 12.339),
        (76.56, 12.339),
    ]
)


@dataclass
class Mosaic:
    """A tiling of the bbox into non-overlapping rectangular cells."""

    xs: list[float]
    ys: list[float]
    cells: dict[tuple[int, int], Polygon]


def build_mosaic(
    minx: float,
    miny: float,
    maxx: float,
    maxy: float,
    n_rows: int,
    n_cols: int,
    seed: int,
) -> Mosaic:
    """Build a rectangular mosaic that tiles exactly (no overlaps or gaps).

    Interior cut lines are placed deterministically from a fixed RNG so two
    seeds produce two different but comparable tiling layouts.
    """
    rng = random.Random(seed)
    dx = maxx - minx
    dy = maxy - miny
    xs = [minx]
    xs += sorted(minx + dx * rng.uniform(0.18, 0.82) for _ in range(n_cols - 1))
    xs.append(maxx)
    ys = [miny]
    ys += sorted(miny + dy * rng.uniform(0.18, 0.82) for _ in range(n_rows - 1))
    ys.append(maxy)

    cells: dict[tuple[int, int], Polygon] = {}
    for row in range(n_rows):
        for col in range(n_cols):
            cells[(row, col)] = Polygon(
                [
                    (xs[col], ys[row]),
                    (xs[col + 1], ys[row]),
                    (xs[col + 1], ys[row + 1]),
                    (xs[col], ys[row + 1]),
                ]
            )
    return Mosaic(xs=xs, ys=ys, cells=cells)


def _cell_key(cells: dict[tuple[int, int], Polygon], point: Point) -> tuple[int, int] | None:
    for key, polygon in cells.items():
        if polygon.covers(point):
            return key
    return None


def find_flip_point(
    cells_a: dict[tuple[int, int], Polygon],
    cells_b: dict[tuple[int, int], Polygon],
    rng: random.Random,
    samples: int = 4000,
) -> tuple[float, float]:
    """Find a deterministic point whose owning cell differs between two layouts.

    Used to place the demo complaint demonstrating that responsibility can
    change when jurisdiction boundaries change between versions.
    """
    margin_x = 0.03 * (WARD_MAXX - WARD_MINX)
    margin_y = 0.03 * (WARD_MAXY - WARD_MINY)
    lo_x, hi_x = WARD_MINX + margin_x, WARD_MAXX - margin_x
    lo_y, hi_y = WARD_MINY + margin_y, WARD_MAXY - margin_y

    for _ in range(samples):
        lon = rng.uniform(lo_x, hi_x)
        lat = rng.uniform(lo_y, hi_y)
        point = Point(lon, lat)
        key_a = _cell_key(cells_a, point)
        key_b = _cell_key(cells_b, point)
        if key_a is not None and key_b is not None and key_a != key_b:
            return lon, lat

    raise RuntimeError("Could not locate a deterministic flip point between layouts")