"""Subject lines for marketing's emails (templates in `templates/emails/`),
keyed [locale][template]; installed with the module's manifest."""

MARKETING_EMAIL_SUBJECTS: dict[str, dict[str, str]] = {
    "en": {"contact-message": "Contact form: {message_subject}"},
    "da": {"contact-message": "Kontaktformular: {message_subject}"},
}
