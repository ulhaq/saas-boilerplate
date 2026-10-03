"""Sync the database's permissions with the installed modules.

Run after migrations on every deploy (and by `init_db`): adds permissions the
platform, billing or the product declare but the database lacks, and grants
them to every organization's Owner role. Idempotent.

Usage:
    uv run python -m src.sync_permissions
"""

import asyncio
import logging

from src.bootstrap import ALL_PERMISSIONS, PERMISSION_DESCRIPTIONS
from src.platform.core.database import ASYNC_SESSION_LOCAL
from src.platform.core.logging import setup_logging
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.services.permission import PermissionSync, sync_permissions

log = logging.getLogger(__name__)

DECLARED: dict[str, str] = {
    permission.value: PERMISSION_DESCRIPTIONS[permission]
    for permission in ALL_PERMISSIONS
}


async def run() -> PermissionSync:
    async with ASYNC_SESSION_LOCAL() as session, session.begin():
        result = await sync_permissions(RepositoryManager(session), DECLARED)
    log.info(
        "Permissions synced: %d added, %d owner grants",
        len(result.added),
        result.granted,
    )
    if result.undeclared:
        log.warning(
            "Permissions no installed module declares (left in place): %s",
            ", ".join(result.undeclared),
        )
    return result


if __name__ == "__main__":
    setup_logging("sync_permissions")
    asyncio.run(run())
