from starlette.applications import Starlette

from ..templates import templates

app = Starlette()

@app.route('/', name='csvtool')
async def index(request):
    """
    Form for uploading CSV
    """
    return templates.TemplateResponse('csv_tool.html', {'request': request})
