import os
import yaml
import copy
import json
import time

from ..templates import templates

with open(os.path.join(os.path.dirname(__file__), './es_config.yml'), 'rb') as yaml_file:
    ES_CONFIG = yaml.safe_load(yaml_file)

with open(os.path.join(os.path.dirname(__file__), './recon_config.yml'), 'rb') as yaml_file:
    RECON_CONFIG = yaml.safe_load(yaml_file)

def search_query(term, orgtype='all'):
    """
    Fetch the search query and insert the query term
    """
    json_q = copy.deepcopy(ES_CONFIG)
    for param in json_q["params"]:
        json_q["params"][param] = term

    # check for organisation type
    if orgtype and orgtype!="all":
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

def recon_query(term):
    """
    Fetch the reconciliation query and insert the query term
    """
    json_q = copy.deepcopy(RECON_CONFIG)
    for param in json_q["params"]:
        json_q["params"][param] = term
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

def random_query(active=False, orgtype=None, aggregate=False):
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

    if orgtype:
        if not isinstance(orgtype, list):
            orgtype = [orgtype]
        query["query"]["function_score"]["query"]["bool"]["must"].append({
            "terms": {
                "organisationType.keyword": orgtype
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

