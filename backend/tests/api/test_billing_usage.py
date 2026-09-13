from datetime import date
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from src.main import app
from src.platform.billing.dependencies import require_limit
from src.platform.models.billing import PlanSetting, PlanUsage
from tests.conftest import TestSessionLocal


class _Metric(StrEnum):
    API_CALLS = "api_calls"


# ---------------------------------------------------------------------------
# Test-only route - exercises require_limit in a real request cycle
# ---------------------------------------------------------------------------

_test_router = APIRouter()


@_test_router.get("/test-limit-gate")
async def _limit_gated_endpoint(
    _: Annotated[None, Depends(require_limit(_Metric.API_CALLS))],
) -> dict:
    return {"ok": True}


app.include_router(_test_router, prefix="/v1")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FREE_PLAN_ID = 1  # seeded in conftest


async def _add_limit(plan_id: int, metric: str, limit_value: int | None) -> None:
    async with TestSessionLocal() as session:
        session.add(PlanSetting(plan_id=plan_id, key=metric, value=limit_value))
        await session.commit()


async def _add_usage(organization_id: int, metric: str, count: int) -> None:
    async with TestSessionLocal() as session:
        session.add(
            PlanUsage(
                organization_id=organization_id,
                metric=metric,
                period_start=date.today().replace(day=1),
                count=count,
            )
        )
        await session.commit()


# ---------------------------------------------------------------------------
# GET /v1/billing/usage
# ---------------------------------------------------------------------------


def test_get_usage_requires_auth(client: TestClient) -> None:
    response = client.get("/v1/billing/usage")
    assert response.status_code == 401


def test_get_usage_empty_when_no_limits_configured(
    admin_authenticated: TestClient,
) -> None:
    response = admin_authenticated.get("/v1/billing/usage")
    assert response.status_code == 200
    rs = response.json()
    assert rs["usage"] == []
    assert rs["period_start"] == date.today().replace(day=1).isoformat()


async def test_get_usage_returns_zero_count_when_no_records(
    admin_authenticated: TestClient,
) -> None:
    await _add_limit(_FREE_PLAN_ID, _Metric.API_CALLS, 1000)

    response = admin_authenticated.get("/v1/billing/usage")
    assert response.status_code == 200
    rs = response.json()
    assert len(rs["usage"]) == 1
    item = rs["usage"][0]
    assert item["metric"] == _Metric.API_CALLS
    assert item["count"] == 0
    assert item["limit"] == 1000


async def test_get_usage_returns_actual_count(
    admin_authenticated: TestClient,
) -> None:
    await _add_limit(_FREE_PLAN_ID, _Metric.API_CALLS, 500)
    await _add_usage(organization_id=1, metric=_Metric.API_CALLS, count=42)

    response = admin_authenticated.get("/v1/billing/usage")
    assert response.status_code == 200
    item = response.json()["usage"][0]
    assert item["count"] == 42
    assert item["limit"] == 500


async def test_get_usage_unlimited_plan_shows_none_limit(
    admin_authenticated: TestClient,
) -> None:
    await _add_limit(_FREE_PLAN_ID, _Metric.API_CALLS, None)

    response = admin_authenticated.get("/v1/billing/usage")
    assert response.status_code == 200
    item = response.json()["usage"][0]
    assert item["limit"] is None


async def test_get_usage_is_org_isolated(
    admin_authenticated: TestClient,
    organization2_admin_authenticated: TestClient,
) -> None:
    await _add_limit(_FREE_PLAN_ID, _Metric.API_CALLS, 100)
    await _add_usage(organization_id=1, metric=_Metric.API_CALLS, count=10)
    await _add_usage(organization_id=2, metric=_Metric.API_CALLS, count=77)

    org1_item = admin_authenticated.get("/v1/billing/usage").json()["usage"][0]
    org2_item = organization2_admin_authenticated.get("/v1/billing/usage").json()[
        "usage"
    ][0]

    assert org1_item["count"] == 10
    assert org2_item["count"] == 77


# ---------------------------------------------------------------------------
# Plan response includes plan_settings
# ---------------------------------------------------------------------------


async def test_plan_list_includes_plan_settings(
    admin_authenticated: TestClient,
) -> None:
    await _add_limit(_FREE_PLAN_ID, _Metric.API_CALLS, 100)

    response = admin_authenticated.get("/v1/billing/plans")
    assert response.status_code == 200
    free_plan = next(p for p in response.json() if p["name"] == "Free")
    assert len(free_plan["plan_settings"]) == 1
    plan_setting = free_plan["plan_settings"][0]
    assert plan_setting["key"] == _Metric.API_CALLS
    assert plan_setting["value"] == 100


def test_plan_list_plan_settings_empty_when_none_configured(
    admin_authenticated: TestClient,
) -> None:
    response = admin_authenticated.get("/v1/billing/plans")
    assert response.status_code == 200
    free_plan = next(p for p in response.json() if p["name"] == "Free")
    assert free_plan["plan_settings"] == []


# ---------------------------------------------------------------------------
# require_limit dependency
# ---------------------------------------------------------------------------


def test_limit_allows_request_when_no_limit_configured(
    admin_authenticated: TestClient,
) -> None:
    response = admin_authenticated.get("/v1/test-limit-gate")
    assert response.status_code == 200


async def test_limit_allows_request_under_limit(
    admin_authenticated: TestClient,
) -> None:
    await _add_limit(_FREE_PLAN_ID, _Metric.API_CALLS, 10)
    await _add_usage(organization_id=1, metric=_Metric.API_CALLS, count=9)

    response = admin_authenticated.get("/v1/test-limit-gate")
    assert response.status_code == 200


async def test_limit_blocks_request_at_limit(
    admin_authenticated: TestClient,
) -> None:
    await _add_limit(_FREE_PLAN_ID, _Metric.API_CALLS, 10)
    await _add_usage(organization_id=1, metric=_Metric.API_CALLS, count=10)

    response = admin_authenticated.get("/v1/test-limit-gate")
    assert response.status_code == 429
    assert response.json()["error_code"] == "limit_exceeded"


async def test_limit_blocks_request_over_limit(
    admin_authenticated: TestClient,
) -> None:
    await _add_limit(_FREE_PLAN_ID, _Metric.API_CALLS, 5)
    await _add_usage(organization_id=1, metric=_Metric.API_CALLS, count=99)

    response = admin_authenticated.get("/v1/test-limit-gate")
    assert response.status_code == 429


async def test_limit_allows_unlimited_plan(
    admin_authenticated: TestClient,
) -> None:
    await _add_limit(_FREE_PLAN_ID, _Metric.API_CALLS, None)
    await _add_usage(organization_id=1, metric=_Metric.API_CALLS, count=9999)

    response = admin_authenticated.get("/v1/test-limit-gate")
    assert response.status_code == 200


async def test_limit_is_org_isolated(
    admin_authenticated: TestClient,
    organization2_admin_authenticated: TestClient,
) -> None:
    await _add_limit(_FREE_PLAN_ID, _Metric.API_CALLS, 5)
    # Only org 2 is at limit
    await _add_usage(organization_id=2, metric=_Metric.API_CALLS, count=5)

    # Org 1 is under limit - allowed
    assert admin_authenticated.get("/v1/test-limit-gate").status_code == 200

    # Org 2 is at limit - blocked
    assert (
        organization2_admin_authenticated.get("/v1/test-limit-gate").status_code == 429
    )
