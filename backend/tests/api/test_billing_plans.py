from fastapi.testclient import TestClient


def test_get_all_plans(admin_authenticated: TestClient, plan_with_price: dict) -> None:
    response = admin_authenticated.get("/v1/billing/plans")
    assert response.status_code == 200
    assert "public" in response.headers["cache-control"]
    plans = response.json()
    assert len(plans) == 2
    plan_names = {p["name"] for p in plans}
    assert "Free" in plan_names
    assert "Pro" in plan_names


def test_get_plan(admin_authenticated: TestClient, plan_with_price: dict) -> None:
    plan_id = plan_with_price["plan"]["id"]
    response = admin_authenticated.get(f"/v1/billing/plans/{plan_id}")
    assert response.status_code == 200
    rs = response.json()
    assert rs["id"] == plan_id
    assert rs["name"] == "Pro"
    assert len(rs["prices"]) == 1


def test_get_plan_not_found(admin_authenticated: TestClient) -> None:
    response = admin_authenticated.get("/v1/billing/plans/9999")
    assert response.status_code == 404
