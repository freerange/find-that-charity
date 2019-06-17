import os
import yaml
import copy
import json
import time

with open(os.path.join(os.path.dirname(__file__), './es_config.yml'), 'rb') as yaml_file:
    ES_CONFIG = yaml.safe_load(yaml_file)

with open(os.path.join(os.path.dirname(__file__), './recon_config.yml'), 'rb') as yaml_file:
    RECON_CONFIG = yaml.safe_load(yaml_file)

def search_query(term):
    """
    Fetch the search query and insert the query term
    """
    json_q = copy.deepcopy(ES_CONFIG)
    for param in json_q["params"]:
        json_q["params"][param] = term
    return json.dumps(json_q)

def recon_query(term):
    """
    Fetch the reconciliation query and insert the query term
    """
    json_q = copy.deepcopy(RECON_CONFIG)
    for param in json_q["params"]:
        json_q["params"][param] = term
    return json.dumps(json_q)

def autocomplete_query(term):
    """
    Look up an organisation using the first part of the name
    """
    return {
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

def random_query(active=False, orgtype=None):
    query = {
        "size": 1,
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
    
    return query

