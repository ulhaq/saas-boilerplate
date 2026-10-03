"""Seat limits (the plan's `seats` setting): pending invitations hold seats,
joining re-checks the limit, and concurrent requests can't both take the last
slot (`BaseService._require_capacity`)."""

import asyncio

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlalchemy import func, select

from src.billing.models.billing import PlanPrice, PlanSetting
from src.foundation.core.exceptions import ClientException
from src.foundation.enums import UsageMetric
from src.foundation.models.invitation import Invitation
from src.foundation.models.user import User
from src.foundation.models.user_organization import UserOrganization
from src.foundation.repositories.repository_manager import RepositoryManager
from src.foundation.services.base import BaseService
from tests.conftest import TestSessionLocal

# Organization 1 is seeded with 3 members.
MEMBERS = 3


async def _set_seats(seats: int) -> None:
    async with TestSessionLocal() as session, session.begin():
        free = (
            await session.execute(select(PlanPrice).where(PlanPrice.amount == 0))
        ).scalar_one()
        session.add(PlanSetting(plan_id=free.plan_id, key="seats", value=seats))


def _invite(mocker: MockerFixture, client: TestClient, email: str):
    send = mocker.patch("src.foundation.services.user.send_email")
    response = client.post("/v1/users/invite", json={"email": email, "role_ids": [2]})
    token = (
        send.call_args.kwargs["data"]["invite_url"].split("token=")[1]
        if response.status_code == 204
        else None
    )
    return response, token


async def _pending_invitations() -> int:
    async with TestSessionLocal() as session:
        return (
            await session.execute(select(func.count()).select_from(Invitation))
        ).scalar_one()


async def test_pending_invitations_hold_seats(
    mocker: MockerFixture,
    admin_authenticated: TestClient,
):
    await _set_seats(MEMBERS + 1)

    response, _ = _invite(mocker, admin_authenticated, "first@example.org")
    assert response.status_code == 204
    response, _ = _invite(mocker, admin_authenticated, "second@example.org")
    assert response.status_code == 402
    assert response.json()["error_code"] == "capacity_exceeded"

    # Re-inviting the same address replaces its invitation - no extra seat.
    response, _ = _invite(mocker, admin_authenticated, "first@example.org")
    assert response.status_code == 204
    assert await _pending_invitations() == 1


async def test_joining_a_full_organization_is_refused_and_the_invite_kept(
    mocker: MockerFixture,
    admin_authenticated: TestClient,
    client: TestClient,
):
    await _set_seats(MEMBERS + 1)
    _, token = _invite(mocker, admin_authenticated, "late@example.org")
    assert token

    # The plan shrinks before the invite is accepted.
    async with TestSessionLocal() as session, session.begin():
        setting = (
            await session.execute(select(PlanSetting).where(PlanSetting.key == "seats"))
        ).scalar_one()
        setting.value = MEMBERS

    body = {"invite_token": token, "name": "Late", "password": "Passw0rd!xyz"}
    response = client.post("/v1/auth/complete-invite", json=body)
    assert response.status_code == 402
    assert response.json()["error_code"] == "capacity_exceeded"
    assert await _pending_invitations() == 1  # usable once a seat frees up


async def test_concurrent_requests_cannot_both_take_the_last_seat():
    await _set_seats(MEMBERS + 1)
    results: list[str] = []

    async def join(email: str) -> None:
        async with TestSessionLocal() as session:
            try:
                async with session.begin():
                    repos = RepositoryManager(session)
                    await BaseService(repos)._require_capacity(
                        UsageMetric.SEATS,
                        1,
                        lambda: repos.user.count_for_org(1),
                    )
                    user = User(name=email, email=email, password="x")
                    session.add(user)
                    await session.flush()
                    session.add(UserOrganization(user_id=user.id, organization_id=1))
                    # Hold the transaction open, so an unlocked check in the
                    # other request would still see the old count.
                    await asyncio.sleep(0.2)
                results.append("joined")
            except ClientException as exc:
                results.append(type(exc).__name__)

    await asyncio.gather(join("a@example.org"), join("b@example.org"))

    assert sorted(results) == ["CapacityExceededException", "joined"]
