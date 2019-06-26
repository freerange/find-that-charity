from starlette.applications import Starlette

from ..db import es
from ..utils import clean_regno, sort_out_date
from ..utils import JSONResponseDate as JSONResponse
from .. import settings
from .orgid import get_orgs_from_orgid, merge_orgs
from ..templates import templates

app = Starlette()

@app.route('/{regno}')
@app.route('/{regno}\.{filetype}')
async def index(request):
    regno = request.path_params['regno']
    filetype = request.path_params.get('filetype', 'html')

    orgid = clean_regno(regno)
    
    orgs = get_orgs_from_orgid(orgid)
    if orgs:
        if filetype == "html":
            return templates.TemplateResponse('org.html', {
                'request': request,
                'orgs': merge_orgs(orgs)
            })
        return JSONResponse(merge_orgs(orgs))
    
    # @TODO: this should be a proper 404 page
    return JSONResponse({
        "error": 'Charity {} not found.'.format(regno)
    }, status_code=404)


@app.route('/{regno}/preview')
async def preview(request):
    regno = request.path_params['regno']

    regno_cleaned = clean_regno(regno)
    if regno_cleaned == "":
        return JSONResponse({
            "error": 'Charity {} not found.'.format(regno)
        }, status_code=404)

    res = es.get(
        index=settings.ES_INDEX,
        doc_type=settings.ES_TYPE,
        id=regno_cleaned,
        _source_exclude=["complete_names"],
        ignore=[404]
    )
    if "_source" in res:
        return templates.TemplateResponse('charity_preview.html', {
            'request': request,
            'charity': sort_out_date(res["_source"]),
            'charity_id': res["_id"]
        })
    else:
        return JSONResponse({
            "error": 'Charity {} not found.'.format(regno)
        }, status_code=404)
