from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status

from src.platform.core.limiter import limiter
from src.platform.schemas.contact import ContactMessageIn, ContactMessageOut
from src.platform.services.contact import ContactService

router = APIRouter(prefix="/contact")


@router.post("", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/minute")
async def submit_contact_message(
    request: Request,
    bg_tasks: BackgroundTasks,
    service: Annotated[ContactService, Depends()],
    schema_in: ContactMessageIn,
) -> ContactMessageOut:
    return await service.submit(schema_in, bg_tasks.add_task)
