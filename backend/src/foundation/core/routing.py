from collections.abc import Sequence
from dataclasses import dataclass

from fastapi import APIRouter

API_PREFIX = "/v1"


@dataclass(frozen=True, kw_only=True)
class RouterMount:
    """A router and how the app mounts it under `API_PREFIX`."""

    router: APIRouter
    tags: Sequence[str]
    # Listed in the public OpenAPI schema for API-token consumers. Every route
    # is in the internal schema the frontend's API types are generated from.
    public: bool = True
