"""Test-run setup that must happen before `conftest.py` imports the app - a
pytest plugin (`-p tests.preload` in pytest.ini), loaded before any conftest.

Sets the environment the settings read at import time, and picks the installed
modules: `TEST_WITHOUT_BILLING=1` runs the suite against an app assembled
without the billing module (CI runs both). Billing's tests (`tests/billing/`
and tests marked `billing`) are then skipped and its fixtures seed nothing, so
the platform and the product are checked to work on their own.
"""

import os

os.environ["RATE_LIMIT_ENABLED"] = "false"
# Never export telemetry from tests, even when .env enables it
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = ""

WITHOUT_BILLING = os.environ.get("TEST_WITHOUT_BILLING") == "1"

if WITHOUT_BILLING:
    # Before anything imports the composition (`src.bootstrap`).
    from src.products import MODULES

    MODULES[:] = [module for module in MODULES if module.name != "billing"]
