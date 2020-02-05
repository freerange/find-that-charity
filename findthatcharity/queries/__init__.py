import os
import copy
import json
import time

from ..templates import templates

with open(os.path.join(os.path.dirname(__file__), './es_config.json'), 'r') as f:
    ES_CONFIG = json.load(f)

with open(os.path.join(os.path.dirname(__file__), './recon_config.json'), 'r') as f:
    RECON_CONFIG = json.load(f)

def search_query(term=None, base_orgtype='all', base_source='all', orgtype='all', source='all',
                 active=False, aggregate=False, p=1, size=10):
    """
    Fetch the search query and insert the query term
    """
    json_q = copy.deepcopy(ES_CONFIG)
    base_query = json_q["source"]["query"]["function_score"]
    if term:
        json_q['params']["name"] = term
    else:
        json_q['source']['sort'] = [{"name.sort": "asc"}]
        base_query["query"]["bool"]["must"] = [
            {"match_all": {}}
        ]
        base_query["functions"] = []

    # check for organisation type
    if orgtype and orgtype != "all" and orgtype!=['']:
        if not isinstance(orgtype, list):
            orgtype = [orgtype]
        base_query["query"]["bool"]["filter"].append({
            "terms": {"organisationType.keyword": orgtype}
        })
    if base_orgtype and base_orgtype != "all" and base_orgtype!=['']:
        if not isinstance(base_orgtype, list):
            base_orgtype = [base_orgtype]
        base_query["query"]["bool"]["filter"].append({
            "terms": {"organisationType.keyword": base_orgtype}
        })

    # check for source
    if source and source != "all" and source!=['']:
        if not isinstance(source, list):
            source = [source]
        base_query["query"]["bool"]["filter"].append({
            "terms": {"sources.keyword": source}
        })
    if base_source and base_source != "all" and base_source!=['']:
        if not isinstance(base_source, list):
            base_source = [base_source]
        base_query["query"]["bool"]["filter"].append({
            "terms": {"sources.keyword": base_source}
        })

    # check for active
    if active:
        base_query["query"]["bool"]["must"].append({
            "match": {
                "active": True
            }
        })
        
    # add aggregates
    if aggregate:
        json_q["source"]["aggs"] = {
            "group_by_type": {
                "terms": {
                    "field": "organisationType.keyword",
                    "size": 500
                }
            },
            "group_by_source": {
                "terms": {
                    "field": "sources.keyword",
                    "size": 500
                }
            }
        }

    json_q["source"]["from"] = (p-1) * size
    json_q["source"]["size"] = size

    return json_q

def recon_query(term, orgtype='all', postcode=None):
    """
    Fetch the reconciliation query and insert the query term
    """
    json_q = copy.deepcopy(RECON_CONFIG)
    for param in json_q["params"]:
        json_q["params"][param] = term

    # add postcode
    if postcode:
        json_q["inline"]["query"]["functions"].append({
            "filter": {
              "term": {
                "postcode": "{{postcode}}"
              }
            },
            "weight": 2
        })
        json_q["params"]["postcode"] = postcode
        
    # check for organisation type
    if orgtype and orgtype != "all":
        if not isinstance(orgtype, list):
            orgtype = [orgtype]
        dis_max = json_q["inline"]["query"]["function_score"]["query"]
        json_q["inline"]["query"]["function_score"]["query"] = {
            "bool": {
                "must": dis_max,
                "filter": {
                    "terms": {"organisationType.keyword": orgtype}
                }
            }
        }

    return json.dumps(json_q)

def autocomplete_query(term, orgtype='all'):
    """
    Look up an organisation using the first part of the name
    """
    doc = {
        "suggest": {
            "suggest-1": {
                "prefix": term,
                "completion": {
                    "field": "complete_names",
                    "fuzzy" : {
                        "fuzziness" : 1
                    }
                }
            }
        }
    }
    
    if not orgtype or orgtype == 'all':
        orgtype = [o['key'] for o in templates.env.globals["org_types"]]

    doc["suggest"]["suggest-1"]["completion"]["contexts"] = {
        "organisationType": orgtype
    }

    return doc



def orgid_query(term):
    """
    Fetch a charity based on their org id
    """

    if not isinstance(term, list):
        term = [term]

    return {
        "query": {
            "terms": {
                "orgIDs.keyword": term
            }
        }
    }

def random_query(active=False, orgtype=None, aggregate=False, source=None):
    query = {
        "query": {
            "function_score": {
                "query": {
                    "bool": {
                        "must": []
                    }
                },
                "boost": "5",
                "random_score": {}, 
                "boost_mode":"multiply"
            }
        }
    }
    if active:
        query["query"]["function_score"]["query"]["bool"]["must"].append({
            "match": {
                "active": True
            }
        })

    if orgtype and orgtype!=['']:
        if not isinstance(orgtype, list):
            orgtype = [orgtype]
        query["query"]["function_score"]["query"]["bool"]["must"].append({
            "terms": {
                "organisationType.keyword": orgtype
            }
        })

    if source and source!=['']:
        if not isinstance(source, list):
            source = [source]
        query["query"]["function_score"]["query"]["bool"]["must"].append({
            "terms": {
                "sources.keyword": source
            }
        })

    if aggregate:
        query["aggs"] = {
            "group_by_type": {
                "terms": {
                    "field": "organisationType.keyword",
                    "size": 500
                }
            },
            "group_by_source": {
                "terms": {
                    "field": "sources.keyword",
                    "size": 500
                }
            }
        }
    
    return query
