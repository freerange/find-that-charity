import json
from urllib.parse import unquote
from collections import OrderedDict

from starlette.applications import Starlette
from starlette.responses import Response

from ..queries import recon_query
from ..db import es
from ..utils import clean_regno
from ..utils import JSONResponseDate as JSONResponse, slugify
from .. import settings
from ..templates import templates

app = Starlette()

@app.route('/propose_properties')
async def propose_properties(request):
    properties = {
        "properties": [
            {
                "id": "active",
                "name": "Active (True/False)"
            },
            {
                "id": "alternateName",
                "name": "List of alternative names"
            },
            {
                "id": "charityNumber",
                "name": "Charity Number"
            },
            {
                "id": "companyNumber",
                "name": "Company numbers"
            },
            {
                "id": "dateRegistered",
                "name": "Date of registration"
            },
            {
                "id": "dateRemoved",
                "name": "Date of removal from the register"
            },
            {
                "id": "postalCode",
                "name": "Postcode"
            },
            {
                "id": "streetAddress",
                "name": "Address street"
            },
            {
                "id": "addressLocality",
                "name": "Address locality"
            },
            {
                "id": "addressRegion",
                "name": "Address region"
            },
            {
                "id": "addressCountry",
                "name": "Address country"
            },
            {
                "id": "telephone",
                "name": "Telephone"
            },
            {
                "id": "email",
                "name": "email"
            },
            {
                "id": "description",
                "name": "Description"
            },
            {
                "id": "organisationType",
                "name": "Type of organisation"
            },
            # {
            #     "id": "domain",
            #     "name": "Web domain"
            # },
            {
                "id": "name",
                "name": "Name"
            },
            {
                "id": "dateModified",
                "name": "Last modified date"
            },
            {
                "id": "latestIncome",
                "name": "Latest income"
            },
            {
                "id": "orgIDs",
                "name": "Organisation identifiers"
            },
            {
                "id": "source",
                "name": "Source"
            },
            {
                "id": "parent",
                "name": "Parent organisation identifier"
            },
            {
                "id": "url",
                "name": "Website"
            },
        ],
        "type": "nonprofit",
        # "limit": 3
    }
    
    if request.query_params.get("callback"):
        return Response("%s(%s);" % (request.query_params.get("callback"), json.dumps(properties)), media_type='application/javascript')
    return JSONResponse(properties)

@app.route('/', methods=['GET', 'POST'])
@app.route('/{orgtype}', methods=['GET', 'POST'])
async def reconcile_index(request):

    orgtypes = request.path_params.get("orgtype", "charity")
    if orgtypes == 'all':
        orgtypes = []
    if orgtypes:
        if orgtypes == 'charity':
            orgtypes = 'registered-charity'
        orgtypes = orgtypes.split("+")
    
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
        
    if queries:
        result = {}
        counter = 0
        for query_id, query in queries.items():
            r = esdoc_orresponse(
                    recon_query(
                        query["query"],
                        [s["key"] for s in templates.env.globals["org_types"].values() if s["slug"] in orgtypes]
                    )
                )["result"]
            result.update({query_id: {"result": r}})
            counter += 1
    elif query:
        result = esdoc_orresponse(
                    recon_query(
                        query,
                        [s["key"] for s in templates.env.globals["org_types"].values() if s["slug"] in orgtypes]
                    )
                )
    elif extend:
        result = extend_with_fields(extend["ids"], extend["properties"])
    else:
        result = service_spec(request, orgtypes)

    # if we're doing a callback request then do that
    if callback:
        return Response("%s(%s);" % (callback, json.dumps(result)), media_type='application/javascript')
    return JSONResponse(result)


def service_spec(request, orgtypes=None):
    """Return the default service specification
    Specification found here: https://github.com/OpenRefine/OpenRefine/wiki/Reconciliation-Service-API#service-metadata
    """
    service_url = "{}://{}".format(
        request.url.scheme,
        request.url.netloc,
    )

    if orgtypes:
        orgtypes = [{
            "id": "/{}".format(s["slug"]),
            "name": s["key"]
        } for s in templates.env.globals["org_types"].values() if s["slug"] in orgtypes]
    else:
        orgtypes = [{
            "id": "/{}".format(s["slug"]),
            "name": s["key"]
        } for s in templates.env.globals["org_types"].values()]

    return {
        "name": "findthatcharity",
        "identifierSpace": "http://rdf.freebase.com/ns/type.object.id",
        "schemaSpace": "http://rdf.freebase.com/ns/type.object.id",
        "view": {
            "url": request.url_for('orgid_html', orgid="{{id}}"),
        },
        "preview": {
            "url": request.url_for('orgid_html', orgid="{{id}}/preview"),
            "width": 430,
            "height": 300
        },
        "defaultTypes": orgtypes,
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
        name = i["_source"]["name"] + " (" + i["_id"] + ")"
        if not i["_source"]["active"]:
            name += " [INACTIVE]"
        hits.append({
            "id": i["_id"],
            "type": [
                slugify(t)
                for t in i["_source"].get("organisationType", [])
                if t
            ],
            "score": i["_score"],
            "name": name,
            "source": i["_source"],
            "match": i["_source"]["name"].lower() == json.loads(query)["params"]["name"].lower() and i["_score"] == res["hits"]["max_score"]
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
                _source_includes=fields_to_include,
                ignore=[404]
            )
            if "_source" in res:
                rows[regno] = res["_source"]

    return {
        "meta": properties, # @todo: to meet the spec here we need to add in names to the properties
        "rows": rows # @todo: these should be in a format specified here: https://github.com/OpenRefine/OpenRefine/wiki/Data-Extension-API
    }
