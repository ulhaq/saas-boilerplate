"""The marketing module's manifest: the public endpoints the marketing site
(`site/`) posts to - waitlist sign-ups and the contact form. Remove it from
`src.products` (and its migration) when the product has no marketing site."""

from pathlib import Path

from src.marketing import models
from src.marketing.emails import MARKETING_EMAIL_SUBJECTS
from src.marketing.gdpr import export_user_data
from src.marketing.routers import contact, waitlist
from src.platform.core.module import Module
from src.platform.core.routing import RouterMount

MARKETING = Module(
    name="marketing",
    models=models,
    routers=[
        RouterMount(router=waitlist.router, tags=["Waitlists"], public=False),
        RouterMount(router=contact.router, tags=["Contact"], public=False),
    ],
    email_subjects=MARKETING_EMAIL_SUBJECTS,
    template_directory=Path(__file__).resolve().parent / "templates",
    user_data_export=export_user_data,
)
