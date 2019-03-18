from starlette.applications import Starlette
from starlette.templating import Jinja2Templates

templates = Jinja2Templates(directory='templates')

app = Starlette()

@app.route('/')
async def index(request):
    """
    Form for uploading CSV
    """
    return templates.TemplateResponse('csv_tool.html', {'request': request})
