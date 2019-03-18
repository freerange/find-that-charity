import json
from urllib.parse import unquote
from collections import OrderedDict

from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response

from ..queries import recon_query
from ..db import es
from .. import settings

app = Starlette()

@app.route('/', methods=['GET', 'POST'])
async def index(request):
    
    query = None
    queries = None
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
    else:
        result = service_spec(service_url)

    if callback:
        return Response("%s(%s);" % (callback, json.dumps(result)), media_type='application/javascript')
    return JSONResponse(result)


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
        }]
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
