from typing import ClassVar

from locust import HttpUser, task

from src.foundation.core.config import settings


class LoadTesting(HttpUser):
    host = settings.app_url
    EXCLUDE_PATHS: ClassVar[list[str]] = ["/users/me"]
    paths: list[str]

    def get_paths(self) -> list[str]:
        res = self.client.get("/openapi.json")
        openapi_schema = res.json()

        rs = []
        for path, path_item in openapi_schema["paths"].items():
            methods = path_item.keys()
            if path in self.EXCLUDE_PATHS or "{" in path or "get" not in methods:
                continue

            rs.append(path)
        return rs

    def on_start(self) -> None:
        self.paths = self.get_paths()

    @task
    def tests(self) -> None:
        for path in self.paths:
            self.client.get(path)
