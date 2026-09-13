from typing import Annotated

from disposable_email_domains import blocklist
from pydantic import AfterValidator, EmailStr, Field, StringConstraints


def _reject_disposable_email(email: str) -> str:
    domain = email.split("@")[-1]
    if domain in blocklist:
        raise ValueError("Disposable email addresses are not allowed")
    return email


ConstrainedEmail = Annotated[
    EmailStr,
    StringConstraints(to_lower=True),
    AfterValidator(_reject_disposable_email),
]
Password = Annotated[str, Field(min_length=8)]
NonEmptyStr = Annotated[str, Field(min_length=1)]
