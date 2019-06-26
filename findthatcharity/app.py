from starlette.applications import Starlette
from starlette.staticfiles import StaticFiles
import uvicorn


from .queries import search_query
from .db import es, fetch_all_sources
from . import settings
from .utils import sort_out_date
from .utils import JSONResponseDate as JSONResponse
from .apps import randcharity, reconcile, charity, autocomplete, orgid, feeds, csvdata
from .templates import templates

app = Starlette()
app.debug = settings.DEBUG
app.mount('/static', StaticFiles(directory="static"))
app.add_route('/random', randcharity.random)
app.add_route('/random.{filetype}', randcharity.random)
app.add_route('/reconcile', reconcile.index, methods=['GET', 'POST'])
app.mount('/reconcile', reconcile.app)
app.mount('/charity', charity.app)
app.mount('/autocomplete', autocomplete.app)
app.mount('/feeds', feeds.app)
app.mount('/orgid', orgid.app)
app.mount('/adddata', csvdata.app)

@app.route('/')
async def homepage(request):
    query = request.query_params.get("q")
    if query:
        query = search_query(query, orgtype=request.query_params.get("orgtype"))
        return search_return(query, request)
    return templates.TemplateResponse('index.html', {
        'request': request,
    })

@app.route('/about')
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

def search_return(query, request):
    """
    Fetch search results and display on a template
    """
    res = es.search_template(
        index=settings.ES_INDEX,
        doc_type=settings.ES_TYPE,
        body=query,
        ignore=[404]
    )
    res = res["hits"]
    for result in res["hits"]:
        result["_link"] = "/orgid/" + result["_id"]
        result["_source"] = sort_out_date(result["_source"])
    
    return templates.TemplateResponse('search.html', {
        'request': request,
        'res': res,
        'term': request.query_params.get("q"),
        'selected_org_type': request.query_params.get("orgtype"),
    })
