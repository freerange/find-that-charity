from datetime import datetime

from starlette.applications import Starlette
from starlette.responses import JSONResponse, RedirectResponse
from starlette.templating import Jinja2Templates
import jinja2

from ..queries import orgid_query
from ..db import es, fetch_all_sources
from .. import settings
from ..utils import sort_out_date

app = Starlette()

SOURCES = fetch_all_sources()

def sources_to_string(sources):
    return ", ".join(sources)
    
templates = Jinja2Templates(directory='templates')
templates.env.filters["sources_to_string"] = sources_to_string
templates.env.globals["sources"] = SOURCES

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

@app.route('/{orgid:path}')
@app.route('/{orgid:path}.html')
async def orgid_html(request):
    """
    Redirect to a record based on the org-id
    """
    orgid = request.path_params['orgid']
    orgs = get_orgs_from_orgid(orgid)
    if orgs:
        return templates.TemplateResponse('org.html', {
            'request': request,
            'orgs': merge_orgs(orgs)
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
        _source_include=["orgIDs"],
        ignore=[404]
    )
    orgids = set()
    if res.get("hits", {}).get("hits", []):
        for org in res["hits"]["hits"]:
            orgids.update(org["_source"]["orgIDs"])

    if not orgids:
        return []

    # do a second search based on the org ids we've found
    res = es.search(
        index=settings.ES_INDEX,
        doc_type=settings.ES_TYPE,
        body=orgid_query(list(orgids)),
        _source_exclude=["complete_names"],
        ignore=[404]
    )
    if res.get("hits", {}).get("hits", []):
        for org in res["hits"]["hits"]:
            org["_source"].update({"id": res["hits"]["hits"][0]["_id"]})
            org["_source"] = sort_out_date(org["_source"])
        return [o["_source"] for o in res["hits"]["hits"]]

def merge_orgs(orgs):
    # @TODO: prioritise based on the source 

    fields = [
        "name", "charityNumber", "companyNumber",
        "telephone", "email", "description", 
        "url", "latestIncome", "dateModified",
        "dateRegistered", "dateRemoved",
        "active", "parent", "organisationType", 
        "alternateName", "orgIDs", "id"
    ]
    data = {}
    sources = set()

    for f in fields:
        data[f] = {}
        for org in orgs:
            if not org.get(f):
                continue

            if isinstance(org[f], list):
                value = org[f]
            else:
                value = [org[f]]

            for v in value:
                if str(v) not in data[f]:
                    data[f][str(v)] = {
                        "value": v,
                        "sources": []
                    }
                data[f][str(v)]["sources"].extend(org["sources"])
                sources.update(org["sources"])

    return {
        "id": list(data["id"].values())[0]["value"],
        "name": list(data["name"].values())[0]["value"],
        "active": list(data["active"].values())[0]["value"] if data["active"] else None,
        "orgs": orgs,
        "data": data,
        "sources": list(sources),
    }
