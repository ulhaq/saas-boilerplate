"""Test-run setup that must happen before `conftest.py` imports the app - a
pytest plugin (`-p tests.preload` in pytest.ini), loaded before any conftest.

Sets the environment the settings read at import time, and picks the installed
modules: `TEST_WITHOUT_MODULES=billing,marketing` runs the suite against an app
assembled without those modules, and `TEST_WITHOUT_MODULES=optional` without
every module that isn't a product (`poe test-platform-only`; CI runs it). Their
tests (`tests/<module>/`, and tests marked with the module's name) are then
skipped and their fixtures seed nothing, so the platform and the product are
checked to work on their own. Each installed module's fixtures
(`tests/<module>/plugin.py`) are loaded too.
"""

import os
from pathlib import Path

os.environ["RATE_LIMIT_ENABLED"] = "false"
# Never export telemetry from tests, even when .env enables it
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = ""

_requested = {
    name.strip()
    for name in os.environ.get("TEST_WITHOUT_MODULES", "").split(",")
    if name.strip()
}
WITHOUT_MODULES: frozenset[str] = frozenset()

if _requested:
    # Before anything imports the composition (`src.bootstrap`).
    from src.products import MODULES, PRODUCTS

    installed = {module.name for module in MODULES}
    if "optional" in _requested:
        _requested.discard("optional")
        _requested |= installed - {product.name for product in PRODUCTS}
    unknown = _requested - installed
    if unknown:
        raise ValueError(f"TEST_WITHOUT_MODULES names unknown modules: {unknown}")
    WITHOUT_MODULES = frozenset(_requested)
    MODULES[:] = [module for module in MODULES if module.name not in WITHOUT_MODULES]


def pytest_configure(config) -> None:
    """Load each installed module's test fixtures (`tests/<module>/plugin.py`),
    so deleting a module's package and its test folder leaves nothing behind."""
    from src.products import MODULES

    for module in MODULES:
        if (Path(__file__).parent / module.name / "plugin.py").exists():
            config.pluginmanager.import_plugin(f"tests.{module.name}.plugin")
