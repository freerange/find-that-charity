from starlette.applications import Starlette
from starlette.responses import JSONResponse

app = Starlette()

@app.route('/')
async def random_charity(request):
    return JSONResponse({'hello': 'world'})
