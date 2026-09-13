from locust import HttpUser, task

from src.platform.core.config import settings


class LoadTesting(HttpUser):
    host = settings.app_url
    EXCLUDE_PATHS: list[str] = ["/users/me"]
    paths: list[str]

    def get_paths(self):
        res = self.client.get("/openapi.json")
        openapi_schema = res.json()

        rs = []
        for path, path_item in openapi_schema["paths"].items():
            methods = path_item.keys()
            if path in self.EXCLUDE_PATHS or "{" in path or "get" not in methods:
                continue

            rs.append(path)
        return rs

    def on_start(self):
        self.paths = self.get_paths()

    @task
    def tests(self):
        for path in self.paths:
            self.client.get(path)
