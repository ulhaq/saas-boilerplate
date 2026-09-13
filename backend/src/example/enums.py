"""Example product enums.

Everything in this module belongs to the example product. The platform enums
(roles, core permissions, billing, audit) live in `src.platform.enums`; this
module contributes the product additions, which the composition root
(`src.bootstrap`) merges into the seeded permission/role sets.

For a new product: rename this package and replace these enums with your own.
"""

from enum import StrEnum

from src.platform.enums import ErrorCodeEnum


class ExamplePermission(StrEnum):
    READ_PROJECT = "read:project"
    CREATE_PROJECT = "create:project"
    UPDATE_PROJECT = "update:project"
    DELETE_PROJECT = "delete:project"


class ExampleAuditAction(StrEnum):
    PROJECT_CREATE = "project.create"
    PROJECT_UPDATE = "project.update"
    PROJECT_DELETE = "project.delete"


class ExampleUsageMetric(StrEnum):
    # Plan setting key capping how many projects an organization may hold.
    PROJECTS = "projects"


class ExampleErrorCode(ErrorCodeEnum):
    PROJECT_NAME_TAKEN = (
        "project_name_taken",
        "A project with this name already exists",
    )


EXAMPLE_PERMISSION_DESCRIPTIONS: dict[ExamplePermission, str] = {
    ExamplePermission.READ_PROJECT: "Allows the user to read projects.",
    ExamplePermission.CREATE_PROJECT: "Allows the user to create projects.",
    ExamplePermission.UPDATE_PROJECT: "Allows the user to update projects.",
    ExamplePermission.DELETE_PROJECT: "Allows the user to delete projects.",
}

# Product-specific copy for the default roles, merged over the generic
# platform descriptions by the composition root. New organizations are seeded
# with only the Owner role, so there are no non-owner default roles to extend.
EXAMPLE_DEFAULT_ROLE_DESCRIPTIONS: dict[str, str] = {}

# Per-role product permission grants, merged into the platform DEFAULT_ROLES by
# the composition root.
EXAMPLE_DEFAULT_ROLE_PERMISSIONS: dict[str, list[ExamplePermission]] = {}
