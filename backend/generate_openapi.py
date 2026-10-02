"""Write the API schemas: `uv run poe openapi`.

- `openapi.json` - the public schema (API-token consumers), as served at /docs.
- `openapi.internal.json` - every route; the frontend's API types are
  generated from it (`npm run gen:api` in `frontend/`).

Both are committed, and CI regenerates them with no `.env` to check they match
the code - so they are built from the code's defaults alone: an empty
environment, and a working directory without the `./.env` settings file.
"""

import json
import os
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parent

os.environ.clear()
with tempfile.TemporaryDirectory() as workdir:
    os.chdir(workdir)
    from src.main import app, internal_openapi

    for path, schema in [
        (BACKEND / "openapi.json", app.openapi()),
        (BACKEND / "openapi.internal.json", internal_openapi()),
    ]:
        path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
