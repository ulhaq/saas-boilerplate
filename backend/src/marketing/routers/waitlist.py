from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from src.marketing.schemas.waitlist import WaitlistJoinIn, WaitlistJoinOut
from src.marketing.services.waitlist import WaitlistService
from src.platform.core.limiter import limiter

router = APIRouter(prefix="/waitlist")


@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def join_waitlist(
    request: Request,  # noqa: ARG001
    service: Annotated[WaitlistService, Depends()],
    schema_in: WaitlistJoinIn,
) -> WaitlistJoinOut:
    return await service.join(schema_in)
