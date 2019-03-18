from starlette.applications import Starlette
from starlette.responses import JSONResponse, RedirectResponse

from ..queries import orgid_query
from ..db import es
from .. import settings

app = Starlette()

@app.route('/{orgid}.json')
async def orgid_json(request):
    """
    Fetch json representation based on a org-id for a record
    """
    orgid = request.path_params['orgid']
    org = get_charity_from_orgid(orgid)
    if org:
        return JSONResponse(org)
    return JSONResponse({
        "error": 'Orgid {} not found.'.format(orgid),
        "query": {"orgid": orgid}
    }, 404)

@app.route('/{orgid}')
@app.route('/{orgid}.html')
async def orgid_html(request):
    """
    Redirect to a record based on the org-id
    """
    orgid = request.path_params['orgid']
    org = get_charity_from_orgid(orgid)
    if org:
        return RedirectResponse('/charity/{}'.format(org["id"]))
    
    # @TODO: this should be a proper 404 page
    return JSONResponse({
        "error": 'Orgid {} not found.'.format(orgid),
        "query": {"orgid": orgid}
    }, 404)

def get_charity_from_orgid(orgid):
    res = es.search(
        index=settings.ES_INDEX,
        doc_type=settings.ES_TYPE,
        body=orgid_query(orgid),
        _source_exclude=["complete_names"],
        ignore=[404]
    )
    if res.get("hits", {}).get("hits", []):
        org = res["hits"]["hits"][0]["_source"]
        org.update({"id": res["hits"]["hits"][0]["_id"]})
        return org
