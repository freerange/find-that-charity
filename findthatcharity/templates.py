import re

from starlette.templating import Jinja2Templates
from slugify import slugify

from .db import fetch_all_sources, value_counts
from .utils import list_to_string
from . import settings

def sort_out_orgtypes(orgtypes):
    return [{
        "key": o["key"],
        "doc_count": o["doc_count"],
        "slug": slugify(o["key"]),
    } for o in orgtypes]

def regex_search(s, regex):
    return re.search(regex, s) is not None

templates = Jinja2Templates(directory='templates')

vals = value_counts()

print(fetch_all_sources())

templates.env.filters["list_to_string"] = list_to_string
templates.env.filters["regex_search"] = regex_search
templates.env.globals["sources"] = fetch_all_sources()
templates.env.globals["org_types"] = sort_out_orgtypes(vals.get("group_by_type", {}).get("buckets",[]))
templates.env.globals["sources_count"] = vals.get("group_by_source", {}).get("buckets", [])
templates.env.globals["key_types"] = settings.KEY_TYPES
