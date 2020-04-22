from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from .queries import search_query, random_query
from .db import es, fetch_all_sources, ORGTYPES
from . import settings
from .utils import JSONResponseDate as JSONResponse, pagination, pagination_request, slugify
from .apps import randcharity, reconcile, charity, autocomplete, orgid, feeds, csvdata, admin
from .templates import templates
from .classes.org import Org

async def index(request):
    query = request.query_params.get("q")

    if query:
        return search_return(
            query,
            request,
        )

    examples = {
        'registered-charity-england-and-wales': 'GB-CHC-1177548',
        'registered-charity-scotland': 'GB-SC-SC007427',
        'registered-charity-northern-ireland': 'GB-NIC-104226',
        'community-interest-company': 'GB-COH-08255580',
        'local-authority': 'GB-LAE-IPS',
        'universities': 'GB-EDU-133808',
    }
    # for r in examples.keys():
    #     org = es.search(
    #         index=settings.ES_INDEX,
    #         doc_type=settings.ES_TYPE,
    #         size=1,
    #         body=random_query(True, orgtype=ORGTYPES[r]['key']),
    #         ignore=[404],
    #         _source=False,
    #     ).get('hits', {}).get('hits', [])
    #     if org:
    #         examples[r] = org[0]["_id"]

    return templates.TemplateResponse('index.html', {
        'request': request,
        'examples': examples
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
    orgtype = ORGTYPES.get(slugify(request.query_params.get("orgtype")), {})
    res = es.search_template(
        index=settings.ES_INDEX,
        doc_type=settings.ES_TYPE,
        body=search_query(
            query,
            orgtype=orgtype.get('key'),
            p=p['p'],
            size=p['size'],
        ),
        ignore=[404],
    )
    
    return templates.TemplateResponse('search.html', {
        'request': request,
        'res': {
            "hits": [Org(o["_id"], **o["_source"]) for o in res.get("hits", {}).get("hits", [])],
            "total": res.get("hits", {}).get("total"),
        },
        'term': request.query_params.get("q"),
        'pages': pagination(p["p"], p["size"], res.get("hits", {}).get("total")),
        'selected_org_type': orgtype.get('slug'),
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
    Mount('/orgid', routes=orgid.routes),
    Mount('/adddata', csvdata.app),
    Mount('/admin', routes=admin.routes, name='admin'),
]
middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_methods=['GET', 'POST', 'OPTIONS'],
        allow_headers=['Origin', 'Accept', 'Content-Type', 'X-Requested-With', 'X-CSRF-Token'],
    )
]

app = Starlette(routes=routes, debug=settings.DEBUG, middleware=middleware)
