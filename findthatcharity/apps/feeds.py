from starlette.applications import Starlette
from starlette.responses import JSONResponse

app = Starlette()

@app.route('/')
async def index(request):
    return JSONResponse({'hello': 'world'})
