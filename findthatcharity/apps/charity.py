from starlette.applications import Starlette

from ..db import es, ORGTYPES, db_con, organisation
from ..utils import JSONResponseDate as JSONResponse
from .. import settings
from .orgid import get_orgs_from_orgid
from ..templates import templates
from ..classes.org import OrgRecord, Org

app = Starlette()

@app.route('/{regno}/preview')
@app.route('/{regno}', name="charity_index")
@app.route('/{regno}\.{filetype}')
async def index(request):
    regno = request.path_params['regno']
    filetype = request.path_params.get('filetype', 'html')

    orgid = OrgRecord.clean_regno(regno)

    template = 'org.html'
    if str(request.url).endswith("/preview"):
        template = 'org_preview.html'
    
    org = Org.from_es(orgid, es, settings.ES_INDEX, settings.ES_TYPE)
    if org:
        org.fetch_records(db_con, organisation)
        org.fetch_org_links(db_con)
        if filetype == "html":
            return templates.TemplateResponse(template, {
                'request': request,
                'org': org,
                'key_types': settings.KEY_TYPES,
                # 'parent_orgs': get_parents(orgs),
                # 'child_orgs': get_children(orgs),
            })
        return JSONResponse(org.as_charity())
    
    # @TODO: this should be a proper 404 page
    return JSONResponse({
        "error": 'Charity {} not found.'.format(regno)
    }, status_code=404)
