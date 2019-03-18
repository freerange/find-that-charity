from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
import uvicorn


from .queries import search_query
from .db import es
from . import settings
from .utils import sort_out_date
from .apps import randcharity, reconcile, charity, autocomplete, orgid, feeds, csvdata

app = Starlette()
app.debug = settings.DEBUG
app.mount('/static', StaticFiles(directory="static"))
app.add_route('/random', randcharity.random)
app.add_route('/random.{filetype}', randcharity.random)
app.mount('/reconcile', reconcile.app)
app.mount('/charity', charity.app)
app.mount('/autocomplete', autocomplete.app)
app.mount('/feeds', feeds.app)
app.mount('/orgid', orgid.app)
app.mount('/adddata', csvdata.app)

templates = Jinja2Templates(directory='templates')

@app.route('/')
async def homepage(request):
    query = request.query_params.get("q")
    if query:
        query = search_query(query)
        return search_return(query, request)
    return templates.TemplateResponse('index.html', {'request': request})

@app.route('/about')
async def about_page(request):
    return templates.TemplateResponse('about.html', {'request': request})

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
        result["_link"] = "/charity/" + result["_id"]
        result["_source"] = sort_out_date(result["_source"])
    
    return templates.TemplateResponse('search.html', {
        'request': request,
        'res': res,
        'term': request.query_params.get("q")
    })
