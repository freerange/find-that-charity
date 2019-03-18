import json
from urllib.parse import unquote
from collections import OrderedDict

from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response

from ..queries import recon_query
from ..db import es
from ..utils import clean_regno
from .. import settings

app = Starlette()

@app.route('/', methods=['GET', 'POST'])
async def index(request):
    
    query = None
    queries = None
    extend = None
    callback = None
    
    form = await request.form()
    if form.get("queries"):
        queries = form["queries"]
        queries = json.loads(unquote(queries), object_pairs_hook=OrderedDict)
    elif request.query_params.get("queries"):
        queries = request.query_params["queries"]
        queries = json.loads(unquote(queries), object_pairs_hook=OrderedDict)
    elif form.get("query"):
        query = form["query"]
    elif request.query_params.get("query"):
        query = request.query_params["query"]
    elif form.get("extend"):
        extend = form["extend"]
        extend = json.loads(unquote(extend), object_pairs_hook=OrderedDict)
    elif request.query_params.get("extend"):
        extend = request.query_params["extend"]
        extend = json.loads(unquote(extend), object_pairs_hook=OrderedDict)

    if "callback" in form:
        callback = form["callback"]
    elif "callback" in  request.query_params:
        callback = request.query_params["callback"]


    service_url = "{}://{}".format(
        request.url.scheme,
        request.url.netloc,
    )
        
    # if we're doing a callback request then do that
    if queries:
        result = {}
        counter = 0
        for query_id, query in queries.items():
            r = esdoc_orresponse(recon_query(query["query"]))["result"]
            result.update({query_id: {"result": r}})
            counter += 1
    elif query:
        result = esdoc_orresponse(recon_query(query))
    elif extend:
        result = extend_with_fields(extend["ids"], extend["properties"])
    else:
        result = service_spec(service_url)

    if callback:
        return Response("%s(%s);" % (callback, json.dumps(result)), media_type='application/javascript')
    return JSONResponse(result)
    

@app.route('/propose_properties')
async def propose_properties(request):
    properties = {
        "properties": [
            {
                "id": "active",
                "name": "Active (True/False)"
            },
            {
                "id": "alt_names",
                "name": "List of alternative names"
            },
            {
                "id": "ccew_link",
                "name": "Charity Commission URL"
            },
            {
                "id": "ccew_number",
                "name": "Charity Commission Number"
            },
            {
                "id": "ccni_link",
                "name": "Charity Commission for Northern Ireland URL"
            },
            {
                "id": "ccni_number",
                "name": "Charity Commission for Northern Ireland Number"
            },
            {
                "id": "oscr_link",
                "name": "Scottish Charity Regulator URL"
            },
            {
                "id": "oscr_number",
                "name": "Scottish Charity Regulator Number"
            },
            {
                "id": "company_number",
                "name": "Company numbers"
            },
            {
                "id": "date_registered",
                "name": "Date of registration"
            },
            {
                "id": "date_removed",
                "name": "Date of removal from the register"
            },
            {
                "id": "geo.postcode",
                "name": "Postcode"
            },
            {
                "id": "domain",
                "name": "Web domain"
            },
            {
                "id": "known_as",
                "name": "Name"
            },
            {
                "id": "last_modified",
                "name": "Last modified date"
            },
            {
                "id": "latest_income",
                "name": "Latest income"
            },
            {
                "id": "org-ids",
                "name": "OrgIDs"
            },
            {
                "id": "parent",
                "name": "Parent charity ID"
            },
            {
                "id": "url",
                "name": "Website"
            },
        ],
        "type": "charity",
        # "limit": 3
    }
    
    if request.query_params.get("callback"):
        return Response("%s(%s);" % (request.query_params.get("callback"), json.dumps(properties)), media_type='application/javascript')
    return JSONResponse(properties)


def service_spec(service_url):
    """Return the default service specification
    Specification found here: https://github.com/OpenRefine/OpenRefine/wiki/Reconciliation-Service-API#service-metadata
    """
    return {
        "name": "findthatcharity",
        "identifierSpace": "http://rdf.freebase.com/ns/type.object.id",
        "schemaSpace": "http://rdf.freebase.com/ns/type.object.id",
        "view": {
            "url": service_url + "/charity/{{id}}"
        },
        "preview": {
            "url": service_url + "/preview/charity/{{id}}",
            "width": 430,
            "height": 300
        },
        "defaultTypes": [{
            "id": "/{}".format(settings.ES_TYPE),
            "name": settings.ES_TYPE
        }],
        "extend": {
            "propose_properties": {
                "service_url": service_url,
                "service_path": "/reconcile/propose_properties"
            },
            "property_settings": []
        },
    }

def esdoc_orresponse(query):
    """Decorate the elasticsearch document to the OpenRefine response API
    Specification found here: https://github.com/OpenRefine/OpenRefine/wiki/Reconciliation-Service-API#service-metadata
    """
    res = es.search_template(
        index=settings.ES_INDEX,
        doc_type=settings.ES_TYPE,
        body=query,
        ignore=[404]
    )
    hits = []
    for i in res["hits"]["hits"]:
        name = i["_source"]["known_as"] + " (" + i["_id"] + ")"
        if not i["_source"]["active"]:
            name += " [INACTIVE]"
        hits.append({
            "id": i["_id"],
            "type": [i["_type"]],
            "score": i["_score"],
            "index": i["_index"],
            "name": name,
            "source": i["_source"],
            "match": i["_source"]["known_as"].lower() == json.loads(query)["params"]["name"].lower() and i["_score"] == res["hits"]["max_score"]
        })
    return {
        "total": len(hits),
        "result": hits,
    }

def extend_with_fields(ids, properties):
    fields_to_include = [p["id"] for p in properties]

    rows = OrderedDict()
    for regno in ids:
        regno_cleaned = clean_regno(regno)
        rows[regno] = {
            p: {} for p in fields_to_include
        }
        if regno_cleaned:
            res = es.get(
                index=settings.ES_INDEX,
                doc_type=settings.ES_TYPE,
                id=regno_cleaned,
                _source_include=fields_to_include,
                ignore=[404]
            )
            if "_source" in res:
                rows[regno] = res["_source"]

    return {
        "meta": properties, # @todo: to meet the spec here we need to add in names to the properties
        "rows": rows # @todo: these should be in a format specified here: https://github.com/OpenRefine/OpenRefine/wiki/Data-Extension-API
    }