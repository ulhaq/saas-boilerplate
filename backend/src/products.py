"""The modules installed in this deployment: optional platform modules
(billing, marketing), then the product.

The only file in the assembly layer that names a product package. To replace
or add a product, change `PRODUCTS`; to run without plans and Stripe, drop
`BILLING`, and without the marketing site's endpoints, `MARKETING` (each with
its migration). `bootstrap`, the API, the worker and Alembic all
read `MODULES`. (The import-linter contracts in `pyproject.toml` name the
product packages too; see `docs/adding-a-domain-module.md`.)
"""

from src.billing.module import BILLING
from src.example.product import EXAMPLE
from src.marketing.module import MARKETING
from src.platform.core.module import Module

PRODUCTS: list[Module] = [EXAMPLE]

MODULES: list[Module] = [BILLING, MARKETING, *PRODUCTS]
