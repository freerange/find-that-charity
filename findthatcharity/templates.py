from starlette.templating import Jinja2Templates

from .utils import list_to_string
from .db import fetch_all_sources
from . import settings

templates = Jinja2Templates(directory='templates')

templates.env.filters["list_to_string"] = list_to_string
templates.env.globals["sources"] = fetch_all_sources()
templates.env.globals["key_types"] = settings.KEY_TYPES