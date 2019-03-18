from starlette.applications import Starlette
from starlette.responses import JSONResponse, RedirectResponse

from ..queries import random_query
from ..db import es
from .. import settings

def random(request):
    """ Get a random charity record
    """
    filetype = request.path_params.get("filetype", "html")
    active = request.path_params.get("active", False)
    res = es.search(
        index=settings.ES_INDEX,
        doc_type=settings.ES_TYPE,
        body=random_query(active),
        ignore=[404]
    )
    char = None
    if "hits" in res:
        if "hits" in res["hits"]:
            char = res["hits"]["hits"][0]

    if char:
        if filetype == "html":
            return RedirectResponse('/charity/{}'.format(char["_id"]))
    return JSONResponse(char["_source"])
