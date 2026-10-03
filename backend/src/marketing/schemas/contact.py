from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from src.platform.schemas.types import ConstrainedEmail

_Trimmed = StringConstraints(strip_whitespace=True)

ContactName = Annotated[str, _Trimmed, Field(min_length=1, max_length=100)]
ContactSubject = Annotated[str, _Trimmed, Field(min_length=1, max_length=150)]
ContactBody = Annotated[str, _Trimmed, Field(min_length=10, max_length=5000)]


class ContactMessageIn(BaseModel):
    name: ContactName
    email: ConstrainedEmail
    subject: ContactSubject
    message: ContactBody
    locale: str | None = None


class ContactMessageOut(BaseModel):
    message: str
