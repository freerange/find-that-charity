import os
import yaml
import copy
import json

with open(os.path.join(os.path.dirname(__file__), './es_config.yml'), 'rb') as yaml_file:
    ES_CONFIG = yaml.load(yaml_file)

with open(os.path.join(os.path.dirname(__file__), './recon_config.yml'), 'rb') as yaml_file:
    RECON_CONFIG = yaml.load(yaml_file)

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
    return {
        "query": {
            "match": {
                "org-ids": {
                    "query": term,
                    "operator": "and",
                }
            }
        }
    }