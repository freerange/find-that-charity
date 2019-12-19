from datetime import datetime

from starlette.applications import Starlette
from starlette.responses import RedirectResponse
import jinja2

from ..queries import orgid_query, random_query
from ..db import es
from .. import settings
from ..utils import JSONResponseDate as JSONResponse
from ..templates import templates
from ..classes.org import MergedOrg, Org

app = Starlette()

@app.route('/type/{orgtype}')
@app.route('/type/{orgtype}.html')
@app.route('/source/{source}')
@app.route('/source/{source}.html')
async def orgid_type(request):
    """
    Show some examples from the type of organisation
    """
    orgtype = [o for o in request.path_params.get('orgtype', "").split("+") if o]
    source = [o for o in request.path_params.get('source', "").split("+") if o]
    res = es.search(
        index=settings.ES_INDEX,
        doc_type=settings.ES_TYPE,
        body=random_query(active=True, orgtype=orgtype, aggregate=True, source=source),
        _source_exclude=["complete_names"],
        ignore=[404]
    )

    return templates.TemplateResponse('orgtype.html', {
        'request': request,
        'res': {
            "hits": [Org(o["_id"], o["_source"]) for o in res.get("hits", {}).get("hits", [])],
            "total": res.get("hits", {}).get("total"),
        },
        'query': orgtype + [templates.env.globals["sources"].get(s, {"publisher": {"name": s}}).get("publisher", {}).get("name", s) for s in source],
        'aggs': res["aggregations"],
    })


@app.route('/{orgid}.json')
async def orgid_json(request):
    """
    Fetch json representation based on a org-id for a record
    """
    orgid = request.path_params['orgid']
    orgs = get_orgs_from_orgid(orgid)
    if orgs:
        return JSONResponse(orgs)
    return JSONResponse({
        "error": 'Orgid {} not found.'.format(orgid),
        "query": {"orgid": orgid}
    }, 404)


@app.route('/{orgid:path}')
@app.route('/{orgid:path}.html')
async def orgid_html(request):
    """
    Find a record based on the org-id
    """
    orgid = request.path_params['orgid']

    template = 'org.html'
    if orgid.endswith("/preview"):
        orgid = orgid[:-8]
        template = 'org_preview.html'

    orgs = get_orgs_from_orgid(orgid)
    if orgs:
        return templates.TemplateResponse(template, {
            'request': request,
            'orgs': orgs,
            'key_types': settings.KEY_TYPES,
            # 'parent_orgs': get_parents(orgs),
            # 'child_orgs': get_children(orgs),
        })
    
    # @TODO: this should be a proper 404 page
    return JSONResponse({
        "error": 'Orgid {} not found.'.format(orgid),
        "query": {"orgid": orgid}
    }, 404)

def get_orgs_from_orgid(orgid):

    # do the first search for orgids
    res = es.search(
        index=settings.ES_INDEX,
        doc_type=settings.ES_TYPE,
        body=orgid_query(orgid),
        _source_exclude=["complete_names"],
        ignore=[404]
    )

    orgids = set()
    if res.get("hits", {}).get("hits", []):
        o = res["hits"]["hits"][0]
        o = Org(o["_id"], o["_source"])
        return MergedOrg(o)

def get_parents(orgs):
    parents = {}
    for k, v in orgs.data["parent"].items():
        if v["value"] not in parents:
            parents[v["value"]] = get_orgs_from_orgid(v["value"])
    return parents

def get_children(orgs):
    children = {}

    res = es.search(
        index=settings.ES_INDEX,
        doc_type=settings.ES_TYPE,
        body={
            "query": {
                "terms": {
                    "parent.keyword": [v["value"] for v in orgs.data["orgIDs"].values()]
                }
            }
        },
        _source_exclude=["complete_names"],
        ignore=[404]
    )

    for o in res.get("hits", {}).get("hits", []):
        if o["_id"] not in children:
            children[o["_id"]] = Org(o["_id"], o["_source"])

    return list(children.values())
