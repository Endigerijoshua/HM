"""Temporal jurisdiction engine tests: resolution + overlap detection (P1)."""
from __future__ import annotations

from datetime import date

from app.db.models.jurisdiction import Jurisdiction, JurisdictionVersion
from app.gis.shapely_provider import ShapelyGeometryProvider
from app.gis.temporal_engine import TemporalJurisdictionEngine
from app.schemas.gis import LookupStatus
from app.seed.seed_runner import _flip_coords


def _engine(db) -> TemporalJurisdictionEngine:
    return TemporalJurisdictionEngine(ShapelyGeometryProvider(db))


def test_matched_ward_lookup(db) -> None:
    result = _engine(db).resolve_jurisdiction_at_point(76.64, 12.28, date(2024, 6, 1))
    assert result.status == LookupStatus.MATCHED
    assert result.jurisdiction is not None
    assert result.jurisdiction.kind == "WARD"
    assert result.version is not None
    assert result.version.code == "DELIM-2024"
    assert result.service_responsibility == "NOT_EVALUATED"


def test_historical_match_uses_previous_version(db) -> None:
    result = _engine(db).resolve_jurisdiction_at_point(76.64, 12.28, date(2023, 6, 1))
    assert result.status == LookupStatus.MATCHED
    assert result.version is not None
    assert result.version.code == "DELIM-2020"
    assert result.version.status == "SUPERSEDED"


def test_flip_point_changes_ward_between_versions(db) -> None:
    """The same coordinate must resolve to different wards on different dates."""
    lon, lat = _flip_coords()
    before = _engine(db).resolve_jurisdiction_at_point(lon, lat, date(2023, 6, 1))
    after = _engine(db).resolve_jurisdiction_at_point(lon, lat, date(2024, 6, 1))
    assert before.status == LookupStatus.MATCHED
    assert after.status == LookupStatus.MATCHED
    assert before.jurisdiction.code != after.jurisdiction.code


def test_no_jurisdiction_in_gap_between_versions(db) -> None:
    """2024-01-01 falls between V1 expiry and V2 effective date."""
    result = _engine(db).resolve_jurisdiction_at_point(76.64, 12.28, date(2024, 1, 1))
    assert result.status == LookupStatus.NO_JURISDICTION


def test_no_jurisdiction_outside_all_windows(db) -> None:
    result = _engine(db).resolve_jurisdiction_at_point(76.64, 12.28, date(2019, 6, 1))
    assert result.status == LookupStatus.NO_JURISDICTION


def test_temporal_boundary_dates(db) -> None:
    """Closed-open semantics: start inclusive, end exclusive."""
    assert (
        _engine(db).resolve_jurisdiction_at_point(76.64, 12.28, date(2020, 1, 1)).status
        == LookupStatus.MATCHED
    )
    # 2023-12-31 is the exclusive end of V1
    assert (
        _engine(db).resolve_jurisdiction_at_point(76.64, 12.28, date(2023, 12, 31)).status
        == LookupStatus.NO_JURISDICTION
    )
    # 2024-04-01 is the inclusive start of V2
    assert (
        _engine(db).resolve_jurisdiction_at_point(76.64, 12.28, date(2024, 4, 1)).status
        == LookupStatus.MATCHED
    )


def test_boundary_point_matches_inclusive(db) -> None:
    # The ward bbox south edge is 12.22; a point on that edge is still inside.
    result = _engine(db).resolve_jurisdiction_at_point(76.6, 12.22, date(2024, 6, 1))
    assert result.status == LookupStatus.MATCHED


def test_corridor_point_resolves_to_nhai(db) -> None:
    result = _engine(db).resolve_jurisdiction_at_point(76.66, 12.337, date(2024, 6, 1))
    assert result.status == LookupStatus.MATCHED
    assert result.jurisdiction.kind == "SPECIAL_CORRIDOR"
    assert result.corridor is not None
    assert result.corridor.code == "ROAD-NH"


def test_invalid_coordinates_status(db) -> None:
    result = _engine(db).resolve_jurisdiction_at_point(200.0, 95.0, date(2024, 6, 1))
    assert result.status == LookupStatus.INVALID_COORDINATES
    assert result.message


def test_matched_ward_includes_ward_ref(db) -> None:
    result = _engine(db).resolve_jurisdiction_at_point(76.64, 12.28, date(2024, 6, 1))
    assert result.ward is not None
    assert result.ward.ward_code.startswith("W-")


def test_no_overlaps_in_seed_data(db) -> None:
    reports = _engine(db).detect_temporal_overlaps()
    assert reports == []


def test_detect_temporal_overlap_after_insert(db) -> None:
    """Insert a duplicate W-01 window overlapping the live one, then roll back."""
    provider = ShapelyGeometryProvider(db)
    engine = TemporalJurisdictionEngine(provider)
    live = (
        db.query(Jurisdiction)
        .filter_by(code="W-01")
        .filter(Jurisdiction.effective_from == date(2024, 4, 1))
        .one()
    )

    db.add(
        Jurisdiction(
            code="W-01",
            name=live.name,
            kind="WARD",
            authority_id=live.authority_id,
            jurisdiction_version_id=live.jurisdiction_version_id,
            geometry_geojson=live.geometry_geojson,
            geometry_wkb=bytes(live.geometry_wkb),
            envelope_geojson=live.envelope_geojson,
            effective_from=date(2024, 5, 1),
            effective_to=None,
            notes="test-duplicate",
        )
    )
    db.flush()

    try:
        reports = provider.all_jurisdictions()
        from app.gis.temporal_engine import _windows_overlap

        assert any(
            _windows_overlap(a.effective_from, a.effective_to, b.effective_from, b.effective_to)
            for a in reports
            for b in reports
            if a.code == "W-01" and a.id != b.id
        )
    finally:
        db.rollback()


def test_temporal_conflict_status_on_overlap(db) -> None:
    """A point covered by two overlapping W-01 rows reports TEMPORAL_CONFLICT."""
    provider = ShapelyGeometryProvider(db)
    engine = TemporalJurisdictionEngine(provider)
    live = (
        db.query(Jurisdiction)
        .filter_by(code="W-01")
        .filter(Jurisdiction.effective_from == date(2024, 4, 1))
        .one()
    )

    db.add(
        Jurisdiction(
            code="W-01",
            name=f"{live.name} (dup)",
            kind="WARD",
            authority_id=live.authority_id,
            jurisdiction_version_id=live.jurisdiction_version_id,
            geometry_geojson=live.geometry_geojson,
            geometry_wkb=bytes(live.geometry_wkb),
            envelope_geojson=live.envelope_geojson,
            effective_from=date(2024, 5, 1),
            effective_to=None,
            notes="test-duplicate",
        )
    )
    db.flush()

    try:
        lon, lat = _inside_point_for(provider, live)
        result = engine.resolve_jurisdiction_at_point(lon, lat, date(2024, 6, 1))
        assert result.status == LookupStatus.TEMPORAL_CONFLICT
        assert "W-01" in (result.message or "")

        reports = engine.detect_temporal_overlaps(on_date=date(2024, 6, 1))
        assert any(r.code == "W-01" and r.count >= 2 for r in reports)
    finally:
        db.rollback()


def _inside_point_for(provider, jurisdiction) -> tuple[float, float]:
    geometry = provider.geometry_for(jurisdiction)
    cx, cy = geometry.centroid.x, geometry.centroid.y
    return float(cx), float(cy)


def test_version_history_query(db) -> None:
    """A jurisdiction code with two versions must return both records."""
    from app.gis.base import sort_jurisdictions

    rows = sort_jurisdictions(db.query(Jurisdiction).filter(Jurisdiction.code == "W-01").all())
    assert len(rows) == 2
    versions = sorted({r.version.code for r in rows})
    assert versions == ["DELIM-2020", "DELIM-2024"]


def test_versions_active_on_dates(db) -> None:
    provider = ShapelyGeometryProvider(db)
    assert provider.version_active_on(date(2023, 6, 1)).code == "DELIM-2020"
    assert provider.version_active_on(date(2024, 6, 1)).code == "DELIM-2024"
    assert provider.version_active_on(date(2024, 1, 1)) is None


def test_area_and_road_lookups(db) -> None:
    provider = ShapelyGeometryProvider(db)
    # V.V. Mohalla area covers (76.605, 12.30)
    area = provider.area_at(76.605, 12.30, date(2024, 6, 1))
    assert area is not None and area.code == "AREA-VVM"
    # Sayyaji Rao Road centreline around (76.615, 12.305)
    road = provider.road_at(76.615, 12.305, date(2024, 6, 1))
    assert road is not None and road.code == "ROAD-SAYYAJI"