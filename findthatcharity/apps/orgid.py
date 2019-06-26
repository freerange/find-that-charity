from datetime import datetime

from starlette.applications import Starlette
from starlette.responses import RedirectResponse
import jinja2

from ..queries import orgid_query, random_query
from ..db import es
from .. import settings
from ..utils import sort_out_date, get_links
from ..utils import JSONResponseDate as JSONResponse
from ..templates import templates

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
    if res.get("hits", {}).get("hits", []):
        for org in res["hits"]["hits"]:
            org["_source"].update({"id": res["hits"]["hits"][0]["_id"]})
            org["_source"] = sort_out_date(org["_source"])

    return templates.TemplateResponse('orgtype.html', {
        'request': request,
        'res': res["hits"],
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
        return JSONResponse(merge_orgs(orgs))
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
    orgs = get_orgs_from_orgid(orgid)
    if orgs:
        return templates.TemplateResponse('org.html', {
            'request': request,
            'orgs': merge_orgs(orgs),
            'key_types': settings.KEY_TYPES,
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

    main_name = list(data["name"].values())[0]["value"]
    names = {}
    for f in ["name", "alternateName"]:
        for k, v in data[f].items():
            if v["value"] == main_name:
                continue
            if k in names:
                names[k]["sources"].extend(v["sources"])
                names[k]["sources"] = list(set(names[k]["sources"]))
            else:
                names[k] = v

    return {
        "id": list(data["id"].values())[0]["value"],
        "name": main_name,
        "names": names,
        "active": list(data["active"].values())[0]["value"] if data["active"] else None,
        "orgs": orgs,
        "data": data,
        "sources": list(sources),
        "links": get_links(data["orgIDs"].keys()),
    }
