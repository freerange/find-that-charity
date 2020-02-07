from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

from .queries import search_query
from .db import es, fetch_all_sources
from . import settings
from .utils import JSONResponseDate as JSONResponse, pagination, pagination_request
from .apps import randcharity, reconcile, charity, autocomplete, orgid, feeds, csvdata
from .templates import templates
from .classes.org import Org

async def index(request):
    query = request.query_params.get("q")

    if query:
        return search_return(
            query,
            request,
        )
    return templates.TemplateResponse('index.html', {
        'request': request,
    })

async def about(request):
    sources = fetch_all_sources()
    publishers = {}
    for s in sources.values():
        if s["publisher"]["name"] not in publishers:
            publishers[s["publisher"]["name"]] = []
        publishers[s["publisher"]["name"]].append(s)

    return templates.TemplateResponse('about.html', {
        'request': request,
        'publishers': publishers,
    })

def search_return(query, request):
    """
    Fetch search results and display on a template
    """
    p = pagination_request(request)
    res = es.search_template(
        index=settings.ES_INDEX,
        doc_type=settings.ES_TYPE,
        body=search_query(
            query,
            orgtype=request.query_params.get("orgtype"),
            p=p['p'],
            size=p['size'],
        ),
        ignore=[404],
    )
    
    return templates.TemplateResponse('search.html', {
        'request': request,
        'res': {
            "hits": [Org(o["_id"], o["_source"]) for o in res.get("hits", {}).get("hits", [])],
            "total": res.get("hits", {}).get("total"),
        },
        'term': request.query_params.get("q"),
        'pages': pagination(p["p"], p["size"], res.get("hits", {}).get("total")),
        'selected_org_type': request.query_params.get("orgtype"),
    })

routes = [
    Route('/', index),
    Route('/about', about),
    Route('/random', randcharity.random),
    Route('/random.{filetype}', randcharity.random),
    Route('/reconcile', reconcile.index, methods=['GET', 'POST']),
    Mount('/static', StaticFiles(directory="static"), name='static'),
    Mount('/reconcile', reconcile.app),
    Mount('/charity', charity.app),
    Mount('/autocomplete', autocomplete.app),
    Mount('/feeds', feeds.app),
    Mount('/orgid', routes=orgid.routes, name='orgid'),
    Mount('/adddata', csvdata.app),
]

app = Starlette(routes=routes, debug=settings.DEBUG)
