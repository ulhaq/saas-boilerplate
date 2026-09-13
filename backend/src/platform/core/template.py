from pathlib import Path

from fastapi.templating import Jinja2Templates
from jinja2 import ChoiceLoader, FileSystemLoader
from markupsafe import Markup, escape

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=_TEMPLATE_DIR)


def add_template_directory(directory: str | Path) -> None:
    """Register an additional template root.

    Called by the composition root (`src.bootstrap`) so product packages can
    ship their own templates without the platform knowing about them.
    """
    env = templates.env
    loader = env.loader
    assert loader is not None
    env.loader = ChoiceLoader([loader, FileSystemLoader(directory)])


def _nl2br(value: str) -> Markup:
    return Markup(escape(value).replace("\n", Markup("<br>\n")))


templates.env.filters["nl2br"] = _nl2br
