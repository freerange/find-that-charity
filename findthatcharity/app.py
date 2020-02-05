from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

from .queries import search_query
from .db import es, fetch_all_sources
from . import settings
from .utils import JSONResponseDate as JSONResponse
from .apps import randcharity, reconcile, charity, autocomplete, orgid, feeds, csvdata
from .templates import templates
from .classes.org import Org

DEFAULT_PAGE = 1
DEFAULT_SIZE = 10

async def homepage(request):
    query = request.query_params.get("q")

    try:
        page = int(request.query_params.get("p", DEFAULT_PAGE))
        if page < 1:
            raise ValueError()
    except ValueError:
        page = DEFAULT_PAGE

    try:
        size = int(request.query_params.get("size", DEFAULT_SIZE))
        if size > 50:
            raise ValueError()
    except ValueError:
        size = DEFAULT_SIZE

    if query:
        return search_return(
            search_query(
                query,
                orgtype=request.query_params.get("orgtype"),
                p=page,
                size=size,
            ),
            request,
            p=page,
            size=size,
        )
    return templates.TemplateResponse('index.html', {
        'request': request,
    })

async def about_page(request):
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

def search_return(query, request, p=DEFAULT_PAGE, size=DEFAULT_SIZE):
    """
    Fetch search results and display on a template
    """
    res = es.search_template(
        index=settings.ES_INDEX,
        doc_type=settings.ES_TYPE,
        body=query,
        ignore=[404],
    )
    
    return templates.TemplateResponse('search.html', {
        'request': request,
        'res': {
            "hits": [Org(o["_id"], o["_source"]) for o in res.get("hits", {}).get("hits", [])],
            "total": res.get("hits", {}).get("total"),
        },
        'term': request.query_params.get("q"),
        'page': p,
        'size': size,
        'selected_org_type': request.query_params.get("orgtype"),
    })

routes = [
    Route('/', homepage),
    Route('/about', about_page),
    Route('/random', randcharity.random),
    Route('/random.{filetype}', randcharity.random),
    Route('/reconcile', reconcile.index, methods=['GET', 'POST']),
    Mount('/static', StaticFiles(directory="static")),
    Mount('/reconcile', reconcile.app),
    Mount('/charity', charity.app),
    Mount('/autocomplete', autocomplete.app),
    Mount('/feeds', feeds.app),
    Mount('/orgid', routes=orgid.routes, name='orgid'),
    Mount('/adddata', csvdata.app),
]

app = Starlette(routes=routes, debug=settings.DEBUG)
