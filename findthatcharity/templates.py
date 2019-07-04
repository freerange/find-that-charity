from starlette.templating import Jinja2Templates
from slugify import slugify

from .utils import list_to_string
from .db import fetch_all_sources, value_counts
from . import settings

def sort_out_orgtypes(orgtypes):
    return [{
        "key": o["key"],
        "doc_count": o["doc_count"],
        "slug": slugify(o["key"]),
    } for o in orgtypes]

templates = Jinja2Templates(directory='templates')

vals = value_counts()

templates.env.filters["list_to_string"] = list_to_string
templates.env.globals["sources"] = fetch_all_sources()
templates.env.globals["org_types"] = sort_out_orgtypes(vals.get("group_by_type", {}).get("buckets",[]))
templates.env.globals["sources_count"] = vals["group_by_source"]["buckets"]
templates.env.globals["key_types"] = settings.KEY_TYPES
