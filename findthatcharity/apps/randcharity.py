from starlette.applications import Starlette
from starlette.responses import RedirectResponse

from ..queries import random_query
from ..db import es
from .. import settings
from ..utils import JSONResponseDate as JSONResponse

def random(request):
    """ Get a random charity record
    """
    filetype = request.path_params.get("filetype", "html")
    active = request.path_params.get("active", False)
    res = es.search(
        index=settings.ES_INDEX,
        doc_type=settings.ES_TYPE,
        size=1,
        body=random_query(active, "Registered Charity"),
        ignore=[404]
    )
    char = None
    if "hits" in res:
        if "hits" in res["hits"]:
            char = res["hits"]["hits"][0]

    if char:
        if filetype == "html":
            return RedirectResponse('/orgid/{}'.format(char["_id"]))
    return JSONResponse(char["_source"])
