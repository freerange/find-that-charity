import re
import datetime

from starlette.templating import Jinja2Templates
from humanize import naturaldelta

from .db import fetch_all_sources, value_counts, ORGTYPES, SOURCES
from .utils import list_to_string, slugify
from . import settings

def regex_search(s, regex):
    return re.search(regex, s) is not None

templates = Jinja2Templates(directory='templates')

templates.env.filters["list_to_string"] = list_to_string
templates.env.filters["regex_search"] = regex_search
templates.env.filters["slugify"] = slugify
templates.env.filters["naturaldelta"] = lambda x: naturaldelta(x, minimum_unit="milliseconds")
templates.env.globals["sources"] = fetch_all_sources()
templates.env.globals["org_types"] = ORGTYPES
templates.env.globals["sources_count"] = SOURCES
templates.env.globals["key_types"] = settings.KEY_TYPES
templates.env.globals["now"] = datetime.datetime.now()
