"""
Useful functions for creating queries
"""
from copy import deepcopy
import json
import yaml

# fetch the search query configurations
with open('./es_config.yml', 'rb') as yaml_file:
    ES_SEARCH_QUERY = yaml.load(yaml_file)
with open('./recon_config.yml', 'rb') as yaml_file:
    ES_RECONCILE_QUERY = yaml.load(yaml_file)


def search_query(term):
    """
    Fetch the search query and insert the query term
    """
    json_q = deepcopy(ES_SEARCH_QUERY)
    for param in json_q["params"]:
        json_q["params"][param] = term
    return json.dumps(json_q)


def recon_query(query):
    """
    Fetch the reconciliation query and insert the query term
    """
    if not query:
        return None

    json_q = deepcopy(ES_RECONCILE_QUERY)
    recon_object = {
        "query": "",          # A string to search for. Required.
        "limit": 3,           # An integer to specify how many results to return. Optional.
        # A single string, or an array of strings, specifying the types of result
        # e.g., person, product, ... The actual format of each type depends on the
        # service (e.g., "Q515" as a Wikidata type). Optional.
        "type": "Registered Charity",
        "type_strict": "any", # A string, one of "any", "all", "should". Optional.
        "properties": [],     # Array of json object literals. Optional
    }

    if isinstance(query, str):
        recon_object["query"] = query
    else:
        for i in recon_object:
            if query.get(i):
                recon_object[i] = query.get(i)

    # set the query parameters
    json_q["params"]["name"] = recon_object["query"]

    # set the limit parameter
    json_q["inline"]["size"] = "{{limit}}"
    json_q["params"]["limit"] = recon_object.get("limit", 3)
    
    # set any query properties
    # dict where keys = the parameter/property name, and the value is an object
    # showing what should be added to the elasticsearch query.
    # What gets added depends on how it is specified:
    #  - an object with "query" is added to json_q["inline"]["query"]["function_score"]["query"]["dis_max"]["queries"]
    #  - an object with "function" is added to json_q["inline"]["query"]["function_score"]["functions"]
    properties = {
        "web": {
            "query": {
                "term": {"url.keyword": "{{web}}"}
            }
        },
        "postcode": {
            "function": {
                "filter": {
                    "term": {"postalCode.keyword": "{{postcode}}"}
                },
                "weight": 10
            }
        }
    }
    for i in recon_object.get("properties", []):
        p = i.get("p", i.get("pid"))
        if p in properties:
            json_q["params"][p] = i.get("v")
            if "query" in properties[p]:
                json_q["inline"]["query"]["function_score"]["query"]["dis_max"]["queries"].append(
                    properties[p]["query"])
            if "function" in properties[p]:
                json_q["inline"]["query"]["function_score"]["functions"].append(
                    properties[p]["function"])

    # set organisation type parameter
    if isinstance(recon_object.get("type"), str):
        json_q["params"]["org_type"] = [recon_object.get("type")]
    elif isinstance(recon_object.get("type"), list):
        json_q["params"]["org_type"] = recon_object.get("type")

    # set organisation type queries
    if json_q["params"].get("org_type"):
        if recon_object.get("type_strict") == "should":
            json_q["inline"]["query"]["function_score"]["functions"].append({
                "filter": {
                    "terms": {"organisationType.keyword": json_q["params"]["org_type"]},
                    "weight": 10
                }
            })
        # not sure how to do an "All" query
        # elif recon_object.get("type_strict") == "all":
        else:
            dis_max = json_q["inline"]["query"]["function_score"]["query"]
            json_q["inline"]["query"]["function_score"]["query"] = {
                "bool": {
                    "must": dis_max,
                    "filter": {
                        "terms": {"organisationType.keyword": json_q["params"]["org_type"]}
                    }
                }
            }

    return json_q


def esdoc_orresponse(query, app):
    """Decorate the elasticsearch document to the OpenRefine response API

    Specification found here: https://github.com/OpenRefine/OpenRefine/wiki/Reconciliation-Service-API#service-metadata
    """
    res = app.config["es"].search_template(
        index=app.config["es_index"],
        doc_type=app.config["es_type"],
        body=query,
        ignore=[404]
    )
    return {
        "result": [
            {
                "id": i.get("_id"),
                "name": "{} ({}){}".format(
                    i.get("_source", {}).get("name", ""),
                    i.get("_id"),
                    " [INACTIVE]" if i.get("_source", {}).get("active", True) else "",
                ),
                "type": i.get("_source", {}).get("organisationType", []),
                "score": i.get("_score"),
                "match": (
                    i.get("_source", {}).get("name", "").lower() == query["params"]["name"].lower(
                    ) and i.get("_score") == res["hits"]["max_score"]
                )
            } for i in res["hits"]["hits"]
        ]
    }


def service_spec(app, service_url):
    """Return the default service specification

    Specification found here: https://github.com/OpenRefine/OpenRefine/wiki/Reconciliation-Service-API#service-metadata
    """
    return {
        "name": app.config["es_index"],
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
            "id": "/" + app.config["es_type"],
            "name": app.config["es_type"]
        }]
    }
