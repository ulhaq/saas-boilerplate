"""The example product's emails (templates in `templates/emails/`): subject lines
keyed [locale][template], the notification categories users can opt out of,
and the rules that send them. Installed with the product's manifest."""

from src.example.enums import (
    ExampleHookEvent,
    ExampleNotificationCategory,
    ExamplePermission,
)
from src.foundation.core.module import NotificationCategory, NotificationRule

EXAMPLE_EMAIL_SUBJECTS: dict[str, dict[str, str]] = {
    "en": {"project-created": "New project in {app_name}: {project_name}"},
    "da": {"project-created": "Nyt projekt i {app_name}: {project_name}"},
}

# New projects show in the bell; email is opt-in, as a busy team creates many.
EXAMPLE_NOTIFICATION_CATEGORIES = [
    NotificationCategory(
        key=ExampleNotificationCategory.PROJECTS,
        email=False,
        permission=ExamplePermission.READ_PROJECT,
    ),
]

# Carried out by the foundation's notification service when the event is
# emitted - `ProjectService` only emits it.
EXAMPLE_NOTIFICATION_RULES = [
    NotificationRule(
        event=ExampleHookEvent.PROJECT_CREATED,
        category=ExampleNotificationCategory.PROJECTS,
        notification_type="example.project-created",
        email_template="project-created",
        recipients=ExamplePermission.READ_PROJECT,
        exclude_user="creator_id",
        data=["project_name", "creator_name"],
        links={"projects_url": "/projects"},
    ),
]
