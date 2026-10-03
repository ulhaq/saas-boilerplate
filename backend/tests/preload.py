"""Test-run setup that must happen before `conftest.py` imports the app - a
pytest plugin (`-p tests.preload` in pytest.ini), loaded before any conftest.

Sets the environment the settings read at import time, and picks the installed
modules: `TEST_WITHOUT_MODULES=billing,marketing` runs the suite against an app
assembled without those optional modules (CI runs it with all of them removed).
Their tests (`tests/<module>/`, and tests marked with the module's name) are
then skipped and their fixtures seed nothing, so the platform and the product
are checked to work on their own.
"""

import os

os.environ["RATE_LIMIT_ENABLED"] = "false"
# Never export telemetry from tests, even when .env enables it
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = ""

WITHOUT_MODULES = frozenset(
    name.strip()
    for name in os.environ.get("TEST_WITHOUT_MODULES", "").split(",")
    if name.strip()
)
WITHOUT_BILLING = "billing" in WITHOUT_MODULES

if WITHOUT_MODULES:
    # Before anything imports the composition (`src.bootstrap`).
    from src.products import MODULES

    unknown = WITHOUT_MODULES - {module.name for module in MODULES}
    if unknown:
        raise ValueError(f"TEST_WITHOUT_MODULES names unknown modules: {unknown}")
    MODULES[:] = [module for module in MODULES if module.name not in WITHOUT_MODULES]
