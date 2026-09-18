"""What-If jurisdiction simulator API (P3).

Deterministic, strictly read-only endpoints. Every endpoint returns a
``status`` in all business outcomes and never mutates a live
``jurisdictions``/``jurisdiction_versions``/``routing_rules``/``complaints``
row. A scenario may only be *applied* through the explicit migration flow in a
later phase.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps_whatif import get_whatif_service
from app.db.models.scenarios import SimulationScenario
from app.schemas.whatif import (
    WhatIfScenarioCreateRequest,
    WhatIfScenarioListResponse,
    WhatIfScenarioResponse,
    WhatIfSimulateRequest,
    WhatIfSimulateResponse,
)
from app.whatif.whatif_service import WhatIfSimulationService

router = APIRouter(prefix="/whatif", tags=["whatif"])


@router.get(
    "/scenarios",
    response_model=WhatIfScenarioListResponse,
    summary="List all what-if scenarios",
)
def list_scenarios(
    service: WhatIfSimulationService = Depends(get_whatif_service),
) -> WhatIfScenarioListResponse:
    return service.list_scenarios()


@router.get(
    "/scenarios/{code}",
    response_model=WhatIfScenarioResponse,
    summary="Get a single what-if scenario",
)
def get_scenario(
    code: str,
    service: WhatIfSimulationService = Depends(get_whatif_service),
) -> WhatIfScenarioResponse:
    return service.get_scenario(code)


@router.post(
    "/scenarios",
    response_model=WhatIfScenarioResponse,
    status_code=201,
    summary="Create a deterministic what-if scenario (DRAFT)",
)
def create_scenario(
    request: WhatIfScenarioCreateRequest,
    service: WhatIfSimulationService = Depends(get_whatif_service),
) -> WhatIfScenarioResponse:
    return service.create_scenario(request)


@router.post(
    "/simulate",
    response_model=WhatIfSimulateResponse,
    summary="Simulate live responsibility vs the proposed overlay",
)
def simulate(
    request: WhatIfSimulateRequest,
    service: WhatIfSimulationService = Depends(get_whatif_service),
) -> WhatIfSimulateResponse:
    return service.simulate(
        longitude=request.longitude,
        latitude=request.latitude,
        issue_type_code=request.issue_type_code,
        on_date=request.on_date,
    )
