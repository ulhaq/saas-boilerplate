import json

from src.main import app

with open("./openapi.json", "w", encoding="utf-8") as f:
    f.write(json.dumps(app.openapi(), indent=2))
