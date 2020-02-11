import re
import datetime

from starlette.templating import Jinja2Templates

from .db import fetch_all_sources, value_counts, ORGTYPES, SOURCES
from .utils import list_to_string, slugify
from . import settings

def regex_search(s, regex):
    return re.search(regex, s) is not None

def prioritise_orgids(orgids):
    if len(orgids)==1:
        return orgids
    prefixes = ["-".join(o.split("-")[0:2]) for o in orgids]
    order = [settings.PRIORITIES.index(p) if p in settings.PRIORITIES else len(settings.PRIORITIES) + 1 for p in prefixes]
    return [x for _,x in sorted(zip(order,orgids))]

templates = Jinja2Templates(directory='templates')

templates.env.filters["list_to_string"] = list_to_string
templates.env.filters["regex_search"] = regex_search
templates.env.filters["slugify"] = slugify
templates.env.filters["prioritise"] = prioritise_orgids
templates.env.globals["sources"] = fetch_all_sources()
templates.env.globals["org_types"] = ORGTYPES
templates.env.globals["sources_count"] = SOURCES
templates.env.globals["key_types"] = settings.KEY_TYPES
templates.env.globals["now"] = datetime.datetime.now()
