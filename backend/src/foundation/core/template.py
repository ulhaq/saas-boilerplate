from collections.abc import Callable
from pathlib import Path

from fastapi.templating import Jinja2Templates
from jinja2 import (
    BaseLoader,
    ChoiceLoader,
    Environment,
    FileSystemLoader,
    select_autoescape,
)
from markupsafe import Markup, escape

from src.foundation.core import composition

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


class _ProductTemplateLoader(BaseLoader):
    """The installed products' template roots (from the `Composition`),
    searched after the foundation's own."""

    def get_source(
        self,
        environment: Environment,
        template: str,
    ) -> tuple[str, str | None, Callable[[], bool] | None]:
        directories = composition.current().template_directories
        return FileSystemLoader(directories).get_source(environment, template)


templates = Jinja2Templates(
    env=Environment(
        loader=ChoiceLoader(
            [FileSystemLoader(_TEMPLATE_DIR), _ProductTemplateLoader()],
        ),
        autoescape=select_autoescape(),
    ),
)


def _nl2br(value: str) -> Markup:
    return escape(value).replace("\n", Markup("<br>\n"))


templates.env.filters["nl2br"] = _nl2br
