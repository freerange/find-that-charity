from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
import uvicorn

from . import settings
from .apps import randcharity, reconcile, charity, autocomplete, orgid, feeds

app = Starlette()
app.debug = settings.DEBUG
app.mount('/static', StaticFiles(directory="static"))
app.mount('/random', randcharity.app)
app.mount('/reconcile', reconcile.app)
app.mount('/charity', charity.app)
app.mount('/autocomplete', autocomplete.app)
app.mount('/feeds', feeds.app)
app.mount('/orgid', orgid.app)

templates = Jinja2Templates(directory='templates')

@app.route('/')
async def homepage(request):
    return templates.TemplateResponse('index.html', {'request': request})

@app.route('/about')
async def about_page(request):
    return JSONResponse({'hello': 'world'})
