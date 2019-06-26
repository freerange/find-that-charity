from starlette.applications import Starlette

from ..db import es
from ..utils import clean_regno, sort_out_date
from ..utils import JSONResponseDate as JSONResponse
from .. import settings
from .orgid import get_orgs_from_orgid, merge_orgs
from ..templates import templates

app = Starlette()

@app.route('/{regno}/preview')
@app.route('/{regno}')
@app.route('/{regno}\.{filetype}')
async def index(request):
    regno = request.path_params['regno']
    filetype = request.path_params.get('filetype', 'html')

    orgid = clean_regno(regno)
    
    template = 'org.html'
    if str(request.url).endswith("/preview"):
        template = 'org_preview.html'
    
    orgs = get_orgs_from_orgid(orgid)
    if orgs:
        if filetype == "html":
            return templates.TemplateResponse(template, {
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

    orgid = clean_regno(regno)
    
    orgs = get_orgs_from_orgid(orgid)
    if orgs:
        return templates.TemplateResponse('org_preview.html', {
            'request': request,
            'orgs': merge_orgs(orgs)
        })
    
    # @TODO: this should be a proper 404 page
    return JSONResponse({
        "error": 'Charity {} not found.'.format(regno)
    }, status_code=404)
