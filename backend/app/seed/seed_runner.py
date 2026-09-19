"""Deterministic, offline demo data for the Mysuru-style civic scenario.

IMPORTANT: All boundaries, roads, areas and rules are SYNTHETIC demo data used
to exercise the temporal/versioned jurisdiction engine. Nothing here is real
official GIS data, and the code never calls any external API.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import date
from random import Random

from shapely.geometry import LineString, Polygon
from shapely.geometry import mapping
from shapely.wkb import dumps as wkb_dumps

from app.db.models import (
    Area,
    AuditLog,
    Authority,
    Complaint,
    ComplaintEvent,
    Department,
    EscalationStep,
    IssueType,
    Jurisdiction,
    JurisdictionChange,
    JurisdictionVersion,
    MigrationPlan,
    ResponsibilityConflict,
    Road,
    RoutingRule,
    Service,
    SimulationScenario,
    Ward,
)
from app.gis.shapely_provider import ShapelyGeometryProvider
from app.seed.geometry import (
    HERITAGE_ZONE,
    HERITAGE_ZONE_PROPOSED,
    NH_CORRIDOR,
    build_v1_ward_mosaic,
    build_v2_ward_mosaic,
    find_flip_point,
    find_flip_point_between,
)

logger = logging.getLogger("app.seed")

SYNTHETIC_DISCLAIMER = "SYNTHETIC DEMO DATA - NOT OFFICIAL MYSURU BOUNDARIES"
WARD_NAMES = [
    "Chamaraja",
    "Krishnaraja",
    "Narasimharaja",
    "Chamundeshwari",
    "V.V. Mohalla",
    "Udayagiri",
    "Gokulam",
    "Jayalakshmipuram",
    "Hebbal",
]

AUTHORITY_DEFS = [
    ("A-MCC", "Mysuru City Corporation", "MUNICIPAL"),
    ("A-MUDA", "Mysuru Urban Development Authority", "PLANNING"),
    ("A-PWD", "Karnataka Public Works Department", "STATE"),
    ("A-CESC", "Chamundeshwari Electricity Supply Company", "UTILITY"),
    ("A-NHAI", "National Highways Authority of India", "NATIONAL"),
]

DEPARTMENT_DEFS = [
    ("MCC-D-HS", "Health & Sanitation", "A-MCC"),
    ("MCC-D-RI", "Roads & Infrastructure", "A-MCC"),
    ("MCC-D-WS", "Water Supply & Drainage", "A-MCC"),
    ("MCC-D-SL", "Street Lighting", "A-MCC"),
    ("MCC-D-HP", "Heritage & Public Works", "A-MCC"),
    ("MUDA-D-LL", "Layout & Land Approval", "A-MUDA"),
    ("MUDA-D-INFRA", "Infrastructure Development", "A-MUDA"),
    ("PWD-D-SH", "State Highways", "A-PWD"),
    ("CESC-D-OM", "Maintenance & Repairs", "A-CESC"),
    ("NHAI-D-CO", "Highway Corridor", "A-NHAI"),
]

SERVICE_DEFS = [
    # (code, department, name, category, sla_days)
    ("SVC-GARBAGE", "MCC-D-HS", "Door-to-door Garbage Collection", "sanitation", 2),
    ("SVC-SWEEP", "MCC-D-HS", "Street Sweeping", "sanitation", 1),
    ("SVC-TOILET", "MCC-D-HS", "Public Toilet Maintenance", "sanitation", 3),
    ("SVC-ROAD", "MCC-D-RI", "City Road Repair", "roads", 5),
    ("SVC-DRAIN", "MCC-D-RI", "Storm Water Drain Cleaning", "roads", 4),
    ("SVC-WATER", "MCC-D-WS", "Water Supply Interruption", "water", 1),
    ("SVC-SEWAGE", "MCC-D-WS", "Sewage Overflow", "water", 2),
    ("SVC-LIGHT", "MCC-D-SL", "Street Light Repair", "lighting", 2),
    ("SVC-HERITAGE", "MCC-D-HP", "Heritage Zone Maintenance", "heritage", 3),
    ("SVC-LAYOUT", "MUDA-D-LL", "Layout Approval Inquiry", "planning", 14),
    ("SVC-SHROAD", "PWD-D-SH", "State Highway Repair", "roads", 7),
    ("SVC-POWER", "CESC-D-OM", "Electricity Outage Repair", "utility", 4),
    ("SVC-NH", "NHAI-D-CO", "National Highway Repair", "roads", 3),
]

JURISDICTION_VERSION_DEFS = [
    (
        1, "DELIM-2020", "Delimitation 2020 (V1)", "SUPERSEDED",
        date(2020, 1, 1), date(2023, 12, 31),
        "Synthetic ward layout in force before the 2024 delimitation.",
    ),
    (
        2, "DELIM-2024", "Delimitation 2024 (V2)", "CURRENT",
        date(2024, 4, 1), None,
        "Current synthetic wards; some boundaries moved vs V1 and a heritage "
        "precinct + NH corridor were added.",
    ),
    (
        3, "REZONE-2026-DRAFT", "Proposed Rezone 2026 (V3)", "PROPOSED",
        date(2026, 7, 1), None,
        "Proposed what-if boundary change. Stored as metadata only - live "
        "jurisdiction rows remain untouched until the scenario is applied.",
    ),
]

# Issue-type catalogue: citizen-facing taxonomy plus legacy codes kept routable
# so already-reported complaints remain answerable.
ISSUE_TYPE_DEFS = [
    # (code, name, category, description)
    ("garbage", "Garbage / solid waste", "sanitation",
     "Uncollected or overflowing household and domestic garbage."),
    ("garbage_collection", "Garbage Collection (legacy code)", "sanitation",
     "Legacy issue code kept routable for historical complaints."),
    ("overflowing_bin", "Overflowing public bin", "sanitation",
     "Public waste bin that needs emptying."),
    ("illegal_dumping", "Illegal dumping of waste", "sanitation",
     "Waste dumped on roads, public land or empty lots."),
    ("street_sweeping", "Street Sweeping (legacy code)", "sanitation",
     "Legacy issue code for street sweeping."),
    ("public_toilet", "Public Toilet (legacy code)", "sanitation",
     "Legacy issue code for public toilet maintenance."),
    ("pothole", "Pothole on city road", "roads",
     "A crater or pothole on a city/collector road."),
    ("road_repair", "Road Repair (legacy code)", "roads",
     "Legacy issue code for city road repair."),
    ("road_damage", "Road surface damage", "roads",
     "Cracked, sunken or otherwise damaged road surface."),
    ("drain_cleaning", "Drain Cleaning (legacy code)", "roads",
     "Legacy issue code for storm-water drain cleaning."),
    ("drainage", "Blocked storm-water drain", "roads",
     "Storm-water drain blocked with silt or debris."),
    ("water_supply", "Water supply interruption", "water",
     "Low pressure or no water from the public supply."),
    ("sewage", "Sewage leak / overflow", "water",
     "Raw sewage leaking from a manhole or line."),
    ("sewage_overflow", "Sewage Overflow (legacy code)", "water",
     "Legacy issue code for sewage overflow."),
    ("streetlight", "Street light not working", "lighting",
     "A public street light that is dark, flickering or damaged."),
    ("street_light", "Street Light (legacy code)", "lighting",
     "Legacy issue code for street lighting faults."),
    ("heritage_maintenance", "Heritage zone maintenance", "heritage",
     "Maintenance issues inside a protected heritage precinct."),
    ("layout_approval", "Layout approval inquiry", "planning",
     "Questions on layout and land approval procedures."),
    ("sh_repair", "State Highway Repair", "highways",
     "Damage on a state highway stretch."),
    ("nh_repair", "National Highway Repair", "highways",
     "Damage on a national highway corridor."),
    ("power_outage", "Electricity outage", "utility",
     "Loss of supply or failed street-power infrastructure."),
    ("construction_waste", "Construction waste on public land", "construction",
     "Construction debris dumped on public land or blocking access."),
    ("public_property_damage", "Public property damage", "public_property",
     "Vandalism or damage to parks, benches, signage or civic assets."),
]

# Rule columns: (code, issue_type, dept, service, scope, jurisdiction_code,
#                priority, eff_from, eff_to, rationale)
RULE_DEFS = [
    ("RULE-GARBAGE-PRE2024", "garbage_collection", "MCC-D-HS", "SVC-GARBAGE", "AUTHORITY_WIDE", None, 1,
     date(2020, 1, 1), date(2023, 12, 31),
     "Historical pre-2024 collection routing; expired by the 2024 delimitation."),
    ("RULE-GARBAGE-01", "garbage_collection", "MCC-D-HS", "SVC-GARBAGE", "AUTHORITY_WIDE", None, 1,
     date(2024, 4, 1), None, "Current door-to-door garbage collection across MCC wards."),
    ("RULE-SWEEP-01", "street_sweeping", "MCC-D-HS", "SVC-SWEEP", "AUTHORITY_WIDE", None, 2,
     date(2024, 4, 1), None, "Street sweeping is operated by MCC Health & Sanitation."),
    ("RULE-TOILET-01", "public_toilet", "MCC-D-HS", "SVC-TOILET", "AUTHORITY_WIDE", None, 2,
     date(2024, 4, 1), None, "Public toilets under MCC sanitation."),
    ("RULE-ROAD-01", "road_repair", "MCC-D-RI", "SVC-ROAD", "AUTHORITY_WIDE", None, 2,
     date(2024, 4, 1), None, "City-road repair under MCC Roads & Infrastructure."),
    ("RULE-DRAIN-01", "drain_cleaning", "MCC-D-RI", "SVC-DRAIN", "AUTHORITY_WIDE", None, 2,
     date(2024, 4, 1), None, "Storm-water drains cleaned by MCC Roads."),
    ("RULE-WATER-01", "water_supply", "MCC-D-WS", "SVC-WATER", "AUTHORITY_WIDE", None, 2,
     date(2024, 4, 1), None, "Water supply interruptions handled by MCC."),
    ("RULE-SEWAGE-01", "sewage_overflow", "MCC-D-WS", "SVC-SEWAGE", "AUTHORITY_WIDE", None, 2,
     date(2024, 4, 1), None, "Sewage overflow handled by MCC Water Supply & Drainage."),
    ("RULE-LIGHT-01", "street_light", "MCC-D-SL", "SVC-LIGHT", "AUTHORITY_WIDE", None, 2,
     date(2024, 4, 1), None, "Street lighting outages fixed by MCC Street Lighting."),
    ("RULE-HERITAGE-01", "heritage_maintenance", "MCC-D-HP", "SVC-HERITAGE", "JURISDICTION", "HER-01", 1,
     date(2024, 4, 1), None,
     "Heritage-precinct issues route to the MCC Heritage & Public Works unit."),
    ("RULE-LAYOUT-01", "layout_approval", "MUDA-D-LL", "SVC-LAYOUT", "AUTHORITY_WIDE", None, 2,
     date(2024, 4, 1), None, "Layout approval inquiries sit with MUDA."),
    ("RULE-SH-01", "sh_repair", "PWD-D-SH", "SVC-SHROAD", "AUTHORITY_WIDE", None, 2,
     date(2024, 4, 1), None, "State highway repair is PWD's responsibility."),
    ("RULE-POWER-01", "power_outage", "CESC-D-OM", "SVC-POWER", "AUTHORITY_WIDE", None, 2,
     date(2024, 4, 1), None, "Power/outage issues belong to CESC."),
    ("RULE-NH-01", "nh_repair", "NHAI-D-CO", "SVC-NH", "AUTHORITY_WIDE", None, 2,
     date(2024, 4, 1), None,
     "National highway issues route to NHAI nationwide - even when the point "
     "sits geographically inside an MCC ward (used by the conflict demo)."),
]

# P2: citizen-facing taxonomy rules (authority-wide), historical variant and a
# deliberately unresolved ownership conflict for construction waste.
P2_RULE_DEFS = [
    # (code, issue_type, dept, service, scope, jurisdiction_code, priority,
    #  eff_from, eff_to, rationale)
    ("RULE-GARBAGE", "garbage", "MCC-D-HS", "SVC-GARBAGE", "AUTHORITY_WIDE", None, 1,
     date(2024, 4, 1), None,
     "Household and domestic garbage collection across MCC wards."),
    ("RULE-GARBAGE-HIST", "garbage", "MCC-D-HS", "SVC-GARBAGE", "AUTHORITY_WIDE", None, 1,
     date(2020, 1, 1), date(2023, 12, 31),
     "Historical garbage routing used before the 2024 boundary version."),
    ("RULE-OVERFLOW-BIN", "overflowing_bin", "MCC-D-HS", "SVC-GARBAGE", "AUTHORITY_WIDE", None, 2,
     date(2024, 4, 1), None,
     "Overflowing public bins are emptied by MCC Health & Sanitation."),
    ("RULE-ILLEGAL-DUMP", "illegal_dumping", "MCC-D-HS", "SVC-GARBAGE", "AUTHORITY_WIDE", None, 2,
     date(2024, 4, 1), None,
     "Illegal dumping is cleared by MCC Health & Sanitation."),
    ("RULE-POTHOLE", "pothole", "MCC-D-RI", "SVC-ROAD", "AUTHORITY_WIDE", None, 2,
     date(2024, 4, 1), None,
     "City-road potholes are repaired by MCC Roads & Infrastructure."),
    ("RULE-ROAD-DAMAGE", "road_damage", "MCC-D-RI", "SVC-ROAD", "AUTHORITY_WIDE", None, 2,
     date(2024, 4, 1), None,
     "General road-surface damage sits with MCC Roads & Infrastructure."),
    ("RULE-DRAINAGE", "drainage", "MCC-D-RI", "SVC-DRAIN", "AUTHORITY_WIDE", None, 2,
     date(2024, 4, 1), None,
     "Blocked storm-water drains are cleaned by MCC Roads & Infrastructure."),
    ("RULE-STREETLIGHT", "streetlight", "MCC-D-SL", "SVC-LIGHT", "AUTHORITY_WIDE", None, 2,
     date(2024, 4, 1), None,
     "Outdoor lighting faults go to MCC Street Lighting."),
    ("RULE-SEWAGE", "sewage", "MCC-D-WS", "SVC-SEWAGE", "AUTHORITY_WIDE", None, 2,
     date(2024, 4, 1), None,
     "Sewage leaks are handled by MCC Water Supply & Drainage."),
    ("RULE-CW-DEV", "construction_waste", "MCC-D-RI", "SVC-ROAD", "JURISDICTION", "W-05", 1,
     date(2024, 4, 1), None,
     "Construction debris blocking V.V. Mohalla access roads routes to MCC Roads "
     "(demand-side responsibility view)."),
    ("RULE-CW-SAN", "construction_waste", "MCC-D-HS", "SVC-GARBAGE", "JURISDICTION", "W-05", 1,
     date(2024, 4, 1), None,
     "Construction waste in V.V. Mohalla routes to MCC sanitation "
     "(supply-side responsibility view). Equally specific to RULE-CW-DEV on "
     "purpose - this models an unresolved ownership conflict."),
]

# Escalation ladders attached to rules: (rule_code, step_number, authority,
#                                       department, service, note)
ESCALATION_DEFS = [
    ("RULE-POTHOLE", 1, "A-MCC", "MCC-D-RI", "SVC-ROAD",
     "First response: an MCC road crew assesses and patches the pothole."),
    ("RULE-POTHOLE", 2, "A-PWD", "PWD-D-SH", "SVC-SHROAD",
     "Escalated to PWD state-highway units when the stretch is a state highway "
     "or the damage exceeds city-road scope."),
    ("RULE-HERITAGE-01", 1, "A-MCC", "MCC-D-HP", "SVC-HERITAGE",
     "The heritage conservation team responds inside the precinct."),
]

# (seed, issue_type, lat, lng, status, locality, description)
COMPLAINT_DEFS = [
    (1001, "garbage_collection", 0.0, 0.0, "OPEN", "Udayagiri pocket",
     "Delimitation 2024 moved this pocket to a different ward (temporal "
     "routing demo). Coordinates computed deterministically by the seed."),
    (1002, "water_supply", 12.3125, 76.6375, "OPEN", "V.V. Mohalla precinct",
     "Sits inside the proposed V3 rezone (what-if + migration demo)."),
    (1003, "nh_repair", 12.2950, 76.6100, "OPEN", "Sayyaji Rao Road",
     "Geographically inside an MCC ward but the rule routes to NHAI. "
     "SYNTHETIC DEMO DATA."),
    (1004, "street_light", 12.2650, 76.6320, "OPEN", "KRS Road",
     "Street lamp flickering outside a commercial block."),
    (1005, "garbage_collection", 12.2900, 76.6650, "IN_PROGRESS", "Gokulam",
     "Overflowing bin beside the Gokulam market entrance."),
    (1006, "water_supply", 12.2430, 76.5920, "RESOLVED", "Chamaraja ward",
     "Low water pressure reported; resolved after pump repair."),
    (1007, "road_repair", 12.3100, 76.6480, "OPEN", "Jayalakshmipuram",
     "Pothole cluster on a collector road."),
    (1008, "power_outage", 12.3200, 76.6150, "OPEN", "Gokulam",
     "Cluster of street lights out near the temple road."),
    (1009, "heritage_maintenance", 12.3120, 76.6380, "OPEN", "Heritage precinct",
     "Graffiti cleanup near the heritage precinct boundary."),
]

FLIP_RNG_SEED = 7
MOSAIC_V1_SEED = 11
MOSAIC_V2_SEED = 23


@dataclass
class SeedStats:
    """Row counts produced by the seed - useful for dashboards and tests."""

    authorities: int = 0
    departments: int = 0
    services: int = 0
    issue_types: int = 0
    escalation_steps: int = 0
    jurisdiction_versions: int = 0
    jurisdictions: int = 0
    jurisdiction_changes: int = 0
    wards: int = 0
    areas: int = 0
    roads: int = 0
    routing_rules: int = 0
    complaints: int = 0
    complaint_events: int = 0
    conflicts: int = 0
    scenarios: int = 0
    migration_plans: int = 0

    @property
    def summary(self) -> dict:
        return asdict(self)


def _geometry_payload(geometry) -> tuple[str, bytes, str]:
    geojson = json.dumps(mapping(geometry))
    wkb_raw = bytes(wkb_dumps(geometry))
    envelope = json.dumps(mapping(geometry.envelope))
    return geojson, wkb_raw, envelope


def _flip_coords() -> tuple[float, float]:
    """Recompute the deterministic coordinate whose ward differs V1 vs V2."""
    return find_flip_point_between(
        build_v1_ward_mosaic().cells,
        build_v2_ward_mosaic().cells,
        Random(FLIP_RNG_SEED),
    )


def seed_all(session) -> SeedStats:
    """Idempotently populate the database with deterministic demo data."""
    if session.query(Authority).count():
        logger.info("Database already seeded - skipping.")
        return _collect_stats(session)

    authorities = _seed_authorities(session)
    departments = _seed_departments(session, authorities)
    services = _seed_services(session, departments)
    _seed_issue_types(session)
    versions = _seed_versions(session)

    by_code = _seed_jurisdictions(session, authorities, versions)
    session.flush()

    _seed_changes(session, versions, by_code)
    _seed_wards_areas_roads(session, versions, by_code)
    _seed_rules(session, authorities, departments, services, by_code)
    complaints = _seed_complaints(session)
    _seed_conflicts(session, complaints)
    _seed_scenarios(session)

    stats = _collect_stats(session)
    session.flush()
    _seed_audit(session, stats)
    return stats


def _seed_authorities(session) -> dict:
    authorities: dict = {}
    for code, name, a_type in AUTHORITY_DEFS:
        authority = Authority(code=code, name=name, authority_type=a_type, description=SYNTHETIC_DISCLAIMER)
        session.add(authority)
        authorities[code] = authority
    session.flush()
    return authorities


def _seed_departments(session, authorities) -> dict:
    departments: dict = {}
    for code, name, authority_code in DEPARTMENT_DEFS:
        department = Department(
            code=code, name=name, authority_id=authorities[authority_code].id,
            description=SYNTHETIC_DISCLAIMER,
        )
        session.add(department)
        departments[code] = department
    session.flush()
    return departments


def _seed_services(session, departments) -> dict:
    services: dict = {}
    for code, department_code, name, category, sla in SERVICE_DEFS:
        service = Service(
            code=code, name=name, department_id=departments[department_code].id,
            category=category, sla_days=sla, description=SYNTHETIC_DISCLAIMER,
        )
        session.add(service)
        services[code] = service
    session.flush()
    return services


def _seed_issue_types(session) -> None:
    for code, name, category, description in ISSUE_TYPE_DEFS:
        session.add(IssueType(
            code=code, name=name, category=category,
            description=description, is_active=True,
        ))
    session.flush()


def _seed_versions(session) -> dict:
    versions: dict = {}
    for version_no, code, name, status, eff_from, eff_to, description in JURISDICTION_VERSION_DEFS:
        version = JurisdictionVersion(
            version_no=version_no, code=code, name=name, status=status,
            effective_from=eff_from, effective_to=eff_to, description=description,
            created_by="seed",
        )
        session.add(version)
        versions[code] = version
    session.flush()
    return versions


def _add_jurisdiction(
    session,
    *,
    code: str,
    name: str,
    kind: str,
    authority_id: int,
    version_id: int,
    polygon,
    eff_from: date,
    eff_to: date | None,
    notes: str,
) -> Jurisdiction:
    geojson, wkb_raw, envelope = _geometry_payload(polygon)
    row = Jurisdiction(
        code=code, name=name, kind=kind,
        authority_id=authority_id,
        jurisdiction_version_id=version_id,
        geometry_geojson=geojson,
        geometry_wkb=wkb_raw,
        envelope_geojson=envelope,
        effective_from=eff_from,
        effective_to=eff_to,
        notes=notes,
    )
    session.add(row)
    return row


def _seed_jurisdictions(session, authorities, versions) -> dict:
    mcc = authorities["A-MCC"].id
    nhai = authorities["A-NHAI"].id
    v1 = versions["DELIM-2020"].id
    v2 = versions["DELIM-2024"].id

    mosaic_v1 = build_v1_ward_mosaic()
    mosaic_v2 = build_v2_ward_mosaic()

    by_code: dict = {}

    for index, ((_row, _col), polygon) in enumerate(sorted(mosaic_v1.cells.items())):
        wcode = f"W-{index + 1:02d}"
        row = _add_jurisdiction(
            session, code=wcode, name=WARD_NAMES[index], kind="WARD",
            authority_id=mcc, version_id=v1, polygon=polygon,
            eff_from=date(2020, 1, 1), eff_to=date(2023, 12, 31),
            notes=f"{SYNTHETIC_DISCLAIMER} (V1 ward)",
        )
        by_code[(wcode, "V1")] = row

    nh_old = _add_jurisdiction(
        session, code="NH-OLD", name="NH-766 Corridor (old)", kind="SPECIAL_CORRIDOR",
        authority_id=nhai, version_id=v1, polygon=NH_CORRIDOR,
        eff_from=date(2020, 1, 1), eff_to=date(2023, 12, 31),
        notes=SYNTHETIC_DISCLAIMER,
    )
    by_code[("NH-OLD", "V1")] = nh_old

    for index, ((_row, _col), polygon) in enumerate(sorted(mosaic_v2.cells.items())):
        wcode = f"W-{index + 1:02d}"
        row = _add_jurisdiction(
            session, code=wcode, name=WARD_NAMES[index], kind="WARD",
            authority_id=mcc, version_id=v2, polygon=polygon,
            eff_from=date(2024, 4, 1), eff_to=None,
            notes=f"{SYNTHETIC_DISCLAIMER} (V2 ward)",
        )
        by_code[(wcode, "V2")] = row

    nh_new = _add_jurisdiction(
        session, code="NH-NEW", name="NH-766 Corridor", kind="SPECIAL_CORRIDOR",
        authority_id=nhai, version_id=v2, polygon=NH_CORRIDOR,
        eff_from=date(2024, 4, 1), eff_to=None,
        notes="SYNTHETIC DEMO DATA - corridor band retains NHAI responsibility",
    )
    by_code[("NH-NEW", "V2")] = nh_new

    heritage = _add_jurisdiction(
        session, code="HER-01", name="Heritage Precinct - Palace Zone", kind="HERITAGE_ZONE",
        authority_id=mcc, version_id=v2, polygon=HERITAGE_ZONE,
        eff_from=date(2024, 4, 1), eff_to=None,
        notes="SYNTHETIC DEMO DATA - overlay jurisdiction used by heritage rules",
    )
    by_code[("HER-01", "V2")] = heritage
    session.flush()
    return by_code


def _add_change(
    session,
    version: JurisdictionVersion,
    from_row: Jurisdiction | None,
    to_row: Jurisdiction | None,
    change_type: str,
    reason: str,
    applied_date: date,
) -> None:
    session.add(JurisdictionChange(
        jurisdiction_version_id=version.id,
        from_jurisdiction_id=from_row.id if from_row else None,
        to_jurisdiction_id=to_row.id if to_row else None,
        change_type=change_type,
        reason=reason,
        applied_date=applied_date,
    ))


def _seed_changes(session, versions, by_code) -> None:
    v2 = versions["DELIM-2024"]

    for wcode in [f"W-{i:02d}" for i in range(1, 10)]:
        row_v1 = by_code.get((wcode, "V1"))
        row_v2 = by_code.get((wcode, "V2"))
        if row_v1 and row_v2 and row_v1.geometry_wkb != row_v2.geometry_wkb:
            _add_change(session, v2, row_v1, row_v2, "MODIFIED",
                        "Delimitation 2024 adjusted ward geometry.", date(2024, 4, 1))
            row_v1.superseded_by_id = row_v2.id

    nh_old = by_code[("NH-OLD", "V1")]
    nh_new = by_code[("NH-NEW", "V2")]
    _add_change(session, v2, nh_old, nh_new, "SUPERSEDED",
                "Corridor registered under the current version.", date(2024, 4, 1))
    nh_old.superseded_by_id = nh_new.id

    heritage = by_code[("HER-01", "V2")]
    _add_change(session, v2, None, heritage, "CREATED",
                "Heritage precinct introduced with the 2024 delimitation.", date(2024, 4, 1))
    session.flush()


def _seed_wards_areas_roads(session, versions, by_code) -> None:
    wards: dict = {}
    for index, name in enumerate(WARD_NAMES):
        row_v2 = by_code[(f"W-{index + 1:02d}", "V2")]
        ward = Ward(
            jurisdiction_id=row_v2.id, ward_code=row_v2.code, name=name,
            locality=f"Synthetic {name} locality",
        )
        session.add(ward)
        wards[f"W-{index + 1:02d}"] = ward
    session.flush()

    area_defs = [
        ("AREA-VVM", "V.V. Mohalla", "W-05",
         Polygon([(76.60, 12.296), (76.615, 12.296), (76.615, 12.305), (76.60, 12.305)])),
        ("AREA-UDAY", "Udayagiri", "W-06",
         Polygon([(76.63, 12.265), (76.645, 12.265), (76.645, 12.272), (76.63, 12.272)])),
        ("AREA-GOK", "Gokulam", "W-07",
         Polygon([(76.655, 12.298), (76.665, 12.298), (76.665, 12.306), (76.655, 12.306)])),
    ]
    for code, name, ward_code, polygon in area_defs:
        geojson, wkb_raw, envelope = _geometry_payload(polygon)
        session.add(Area(
            code=code, name=name, ward_id=wards[ward_code].id,
            geometry_geojson=geojson, geometry_wkb=wkb_raw, envelope_geojson=envelope,
            effective_from=date(2024, 4, 1), effective_to=None,
            description=SYNTHETIC_DISCLAIMER,
        ))

    road_defs = [
        ("ROAD-NH", "NH-766 Corridor", "NH", "NH-NEW",
         LineString([(76.56, 12.337), (76.72, 12.337)])),
        ("ROAD-KRS", "KRS Road", "CITY", "W-05",
         LineString([(76.58, 12.26), (76.60, 12.275)])),
        ("ROAD-SAYYAJI", "Sayyaji Rao Road", "CITY", "W-08",
         LineString([(76.60, 12.30), (76.63, 12.31)])),
        ("ROAD-NANJANGUD", "Mysuru-Nanjangud Road (SH-17)", "SH", "W-09",
         LineString([(76.65, 12.28), (76.68, 12.315)])),
    ]
    for code, name, road_class, jur_code, geometry in road_defs:
        geojson, wkb_raw, envelope = _geometry_payload(geometry)
        session.add(Road(
            code=code, name=name, road_class=road_class,
            jurisdiction_id=by_code[(jur_code, "V2")].id,
            jurisdiction_version_id=versions["DELIM-2024"].id,
            geometry_geojson=geojson, geometry_wkb=wkb_raw, envelope_geojson=envelope,
            effective_from=date(2024, 4, 1), effective_to=None,
            notes=SYNTHETIC_DISCLAIMER,
        ))
    session.flush()


def _seed_rules(session, authorities, departments, services, by_code) -> None:
    for (code, issue, dept_code, svc_code, scope, jur_code, priority,
         eff_from, eff_to, rationale) in RULE_DEFS + P2_RULE_DEFS:
        session.add(RoutingRule(
            code=code,
            issue_type_code=issue,
            authority_id=departments[dept_code].authority_id,
            department_id=departments[dept_code].id,
            service_id=services[svc_code].id,
            scope=scope,
            jurisdiction_id=by_code[(jur_code, "V2")].id if jur_code else None,
            match_geography=True,
            priority=priority,
            effective_from=eff_from,
            effective_to=eff_to,
            rationale=rationale,
        ))
    session.flush()

    for (rule_code, step_number, authority_code, dept_code, svc_code, note) in ESCALATION_DEFS:
        rule = session.query(RoutingRule).filter(RoutingRule.code == rule_code).one()
        session.add(EscalationStep(
            routing_rule_id=rule.id,
            step_number=step_number,
            authority_id=authorities[authority_code].id,
            department_id=departments[dept_code].id,
            service_id=services[svc_code].id,
            note=note,
        ))
    session.flush()


def _ward_at(session, longitude: float, latitude: float) -> Ward | None:
    provider = ShapelyGeometryProvider(session)
    jurisdiction = provider.jurisdiction_at(longitude, latitude, date(2024, 6, 1))
    if jurisdiction and jurisdiction.kind == "WARD":
        return session.query(Ward).filter(Ward.jurisdiction_id == jurisdiction.id).first()
    return None


def _seed_complaints(session) -> dict:
    flip_lon, flip_lat = _flip_coords()
    complaints: dict = {}
    for seed, issue, lat, lng, status, locality, description in COMPLAINT_DEFS:
        lat, lng = (flip_lat, flip_lon) if seed == 1001 else (lat, lng)
        ward = _ward_at(session, lng, lat)
        complaint = Complaint(
            public_ref=f"C-{seed}", lat=lat, lng=lng, issue_type_code=issue,
            description=description, status=status, locality=locality,
            ward_id=ward.id if ward else None, source="demo-seed",
        )
        session.add(complaint)
        complaints[f"C-{seed}"] = complaint
        session.flush()
        session.add(ComplaintEvent(
            complaint_id=complaint.id, event_type="CREATED",
            from_status=None, to_status=status,
            note="Seeded demo complaint.", actor="seed",
        ))
    session.flush()
    return complaints


def _seed_conflicts(session, complaints) -> None:
    complaint = complaints["C-1003"]
    mcc = session.query(Authority).filter(Authority.code == "A-MCC").one()
    nhai = session.query(Authority).filter(Authority.code == "A-NHAI").one()
    session.add(ResponsibilityConflict(
        code="CF-1001", status="OPEN", conflict_type="GEO_VS_SERVICE",
        lat=complaint.lat, lng=complaint.lng, complaint_id=complaint.id,
        geo_authority_id=mcc.id, service_authority_id=nhai.id,
        description="Point lies geographically inside an MCC ward, but the "
                    "nh_repair service rule routes responsibility to NHAI. "
                    "SYNTHETIC DEMO DATA.",
    ))
    session.flush()


def _seed_scenarios(session) -> None:
    # The SC-V3-REZONE scenario carries real *proposed* geometry: the V3
    # heritage rezone boundary, stored on the scenario row (geometry_wkb) so
    # the what-if simulator and migration preview read the same proposed
    # boundary at runtime. It deliberately differs from the live HER-01
    # precinct and never reaches the live jurisdictions table.
    geojson, wkb_raw, envelope = _geometry_payload(HERITAGE_ZONE_PROPOSED)
    scenario = SimulationScenario(
        code="SC-V3-REZONE",
        name="V.V. Mohalla Rezone (Proposed 2026)",
        description="Proposed V3 heritage-precinct rezone around V.V. Mohalla. "
                    "Stored as scenario geometry only - isolated from live "
                    "jurisdictions until explicitly applied.",
        status="DRAFT", applies_to="WARD",
        affected_region_name="V.V. Mohalla precinct",
        geometry_geojson=geojson, geometry_wkb=wkb_raw, envelope_geojson=envelope,
        result_summary=None, created_by="demo-admin",
    )
    session.add(scenario)
    session.flush()

    session.add(MigrationPlan(
        code="MP-V3-REZONE-PREVIEW",
        name="V3 Rezone Migration Plan (Preview)",
        scenario_id=scenario.id,
        status="DRAFT", summary=None, affected_count=0,
        created_by="demo-admin",
    ))
    session.flush()


def _seed_audit(session, stats: SeedStats) -> None:
    latest = session.query(JurisdictionVersion).order_by(
        JurisdictionVersion.version_no.desc()
    ).first()
    session.add(AuditLog(
        actor="system", actor_role="seed", action="seed.loaded",
        entity_type="seed", entity_id=None, before_data=None,
        after_data=stats.summary, ip=None, route_reference=None,
    ))
    session.add(AuditLog(
        actor="system", actor_role="seed", action="jurisdiction.version.applied",
        entity_type="jurisdiction_versions",
        entity_id=str(latest.id) if latest else None,
        before_data=None,
        after_data={
            "version_no": latest.version_no if latest else None,
            "code": latest.code if latest else None,
            "status": latest.status if latest else None,
        },
        ip=None, route_reference=None,
    ))


def _collect_stats(session) -> SeedStats:
    return SeedStats(
        authorities=session.query(Authority).count(),
        departments=session.query(Department).count(),
        services=session.query(Service).count(),
        issue_types=session.query(IssueType).count(),
        escalation_steps=session.query(EscalationStep).count(),
        jurisdiction_versions=session.query(JurisdictionVersion).count(),
        jurisdictions=session.query(Jurisdiction).count(),
        jurisdiction_changes=session.query(JurisdictionChange).count(),
        wards=session.query(Ward).count(),
        areas=session.query(Area).count(),
        roads=session.query(Road).count(),
        routing_rules=session.query(RoutingRule).count(),
        complaints=session.query(Complaint).count(),
        complaint_events=session.query(ComplaintEvent).count(),
        conflicts=session.query(ResponsibilityConflict).count(),
        scenarios=session.query(SimulationScenario).count(),
        migration_plans=session.query(MigrationPlan).count(),
    )