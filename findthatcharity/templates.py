from starlette.templating import Jinja2Templates

from .utils import list_to_string
from .db import fetch_all_sources, value_counts
from . import settings

templates = Jinja2Templates(directory='templates')

vals = value_counts()

templates.env.filters["list_to_string"] = list_to_string
templates.env.globals["sources"] = fetch_all_sources()
templates.env.globals["org_types"] = vals["group_by_type"]["buckets"]
templates.env.globals["sources_count"] = vals["group_by_source"]["buckets"]
templates.env.globals["key_types"] = settings.KEY_TYPES
