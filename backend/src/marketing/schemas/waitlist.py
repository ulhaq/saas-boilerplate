from pydantic import BaseModel

from src.foundation.schemas.types import ConstrainedEmail


class WaitlistJoinIn(BaseModel):
    email: ConstrainedEmail
    name: str | None = None


class WaitlistJoinOut(BaseModel):
    message: str
