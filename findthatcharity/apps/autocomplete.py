from starlette.applications import Starlette

from ..db import es
from .. import settings
from ..queries import autocomplete_query
from ..utils import JSONResponseDate as JSONResponse

app = Starlette()

@app.route('/')
async def index(request):
    """
    Endpoint for autocomplete queries
    """
    res = es.search(
        index=settings.ES_INDEX,
        doc_type=settings.ES_TYPE,
        body=autocomplete_query(
            request.query_params.get("q", ""),
            orgtype=request.query_params.get("orgtype", "all"),
        ),
        _source_include=['name', 'organisationType']
    )
    return JSONResponse({
        "results": [
            {
                "label": x["_source"]["name"],
                "value": x["_id"],
                "orgtypes": x["_source"]["organisationType"],
            } for x in res.get("suggest", {}).get("suggest-1", [])[0]["options"]
        ]
    })