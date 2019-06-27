from starlette.applications import Starlette

from ..db import es
from ..utils import JSONResponseDate as JSONResponse
from .. import settings
from .orgid import get_orgs_from_orgid
from ..templates import templates
from ..classes.org import MergedOrg, Org

app = Starlette()

@app.route('/{regno}/preview')
@app.route('/{regno}')
@app.route('/{regno}\.{filetype}')
async def index(request):
    regno = request.path_params['regno']
    filetype = request.path_params.get('filetype', 'html')

    orgid = Org.clean_regno(regno)

    template = 'org.html'
    if str(request.url).endswith("/preview"):
        template = 'org_preview.html'
    
    orgs = get_orgs_from_orgid(orgid)
    if orgs:
        if filetype == "html":
            return templates.TemplateResponse(template, {
                'request': request,
                'orgs': orgs
            })
        return JSONResponse(orgs.as_charity())
    
    # @TODO: this should be a proper 404 page
    return JSONResponse({
        "error": 'Charity {} not found.'.format(regno)
    }, status_code=404)
