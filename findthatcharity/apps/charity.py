from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.templating import Jinja2Templates

from ..db import es
from ..utils import clean_regno, sort_out_date
from .. import settings

app = Starlette()
templates = Jinja2Templates(directory='templates')

@app.route('/{regno}')
@app.route('/{regno}\.{filetype}')
async def index(request):
    regno = request.path_params['regno']
    filetype = request.path_params.get('filetype', 'html')

    regno_cleaned = clean_regno(regno)
    if regno_cleaned == "":
        return JSONResponse({
            "error": 'Charity {} not found.'.format(regno)
        }, status_code=404)

    res = es.get(index=settings.ES_INDEX, doc_type=settings.ES_TYPE, id=regno_cleaned, ignore=[404])
    if "_source" in res:
        if filetype == "html":
            return templates.TemplateResponse('charity.html', {
                'request': request,
                'charity': sort_out_date(res["_source"]),
                'charity_id': res["_id"]
            })
        return JSONResponse(res["_source"])
    else:
        return JSONResponse({
            "error": 'Charity {} not found.'.format(regno)
        }, status_code=404)
