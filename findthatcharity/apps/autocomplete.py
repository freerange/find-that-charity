from starlette.applications import Starlette
from starlette.responses import JSONResponse

from ..db import es
from .. import settings
from ..queries import autocomplete_query

app = Starlette()

@app.route('/')
async def index(request):
    """
    Endpoint for autocomplete queries
    """
    res = es.search(
        index=settings.ES_INDEX,
        doc_type=settings.ES_TYPE,
        body=autocomplete_query(request.query_params.get("q", "")),
        _source_include=['name']
    )
    return JSONResponse({
        "results": [
            {
                "label": x["_source"]["name"],
                "value": x["_id"]
            } for x in res.get("suggest", {}).get("suggest-1", [])[0]["options"]
        ]
    })