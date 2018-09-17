"""
Run the find that charity server
"""
from __future__ import print_function
import os
import argparse
import json
from collections import OrderedDict
import time
from datetime import datetime, timezone
import re

from dateutil import parser
import bottle
from elasticsearch import Elasticsearch
import requests
from bs4 import BeautifulSoup

from queries import search_query, recon_query, service_spec, esdoc_orresponse
from csv_upload import csv_app

app = bottle.default_app()
app.merge(csv_app)

# everywhere gives a different env var for elasticsearch services...
POTENTIAL_ENV_VARS = [
    "ELASTICSEARCH_URL",
    "ES_URL",
    "BONSAI_URL"
]
for e_v in POTENTIAL_ENV_VARS:
    if os.environ.get(e_v):
        app.config["es"] = Elasticsearch(os.environ.get(e_v))
        app.config["es_index"] = 'charitysearch'
        app.config["es_type"] = 'charity'
        break

if os.environ.get("GA_TRACKING_ID"):
    app.config["ga_tracking_id"] = os.environ.get("GA_TRACKING_ID")

if os.environ.get("ADMIN_PASSWORD"):
    app.config["admin_password"] = os.environ.get("ADMIN_PASSWORD")

csv_app.config.update(app.config)


def search_return(query):
    """
    Fetch search results and display on a template
    """
    res = app.config["es"].search_template(
        index=app.config["es_index"],
        doc_type=app.config["es_type"],
        body=query,
        ignore=[404]
    )
    res = res["hits"]
    for result in res["hits"]:
        result["_link"] = "/charity/" + result["_id"]
        result["_source"] = sort_out_date(result["_source"])
    return bottle.template('search', res=res, term=json.loads(query)["params"]["name"])


@app.route('/')
def home():
    """
    Get the index page for the site
    """
    query = bottle.request.query.get('q')
    if query:
        query = search_query(query)
        return search_return(query)
    return bottle.template('index', term='')


@app.route('/random')
@app.route('/random.<filetype>')
def random(filetype="html"):
    """ Get a random charity record
    """
    query = {
        "size": 1,
        "query": {
            "function_score": {
                "functions": [
                    {
                        "random_score": {
                            "seed": str(time.time())
                        }
                    }
                ]
            }
        }
    }

    if "active" in bottle.request.query:
        query["query"]["function_score"]["query"] = {"match": {"active": True}}

    res = app.config["es"].search(
        index=app.config["es_index"],
        doc_type=app.config["es_type"],
        body=query,
        ignore=[404]
    )
    char = None
    if "hits" in res:
        if "hits" in res["hits"]:
            char = res["hits"]["hits"][0]

    if char:
        if filetype == "html":
            bottle.redirect("/charity/{}".format(char["_id"]))
        return char["_source"]



@app.route('/reconcile')
@app.post('/reconcile')
def reconcile():
    """ Index of the server. If ?query or ?queries used then search,
                otherwise return the default response as JSON
    """
    query = recon_query(bottle.request.query.query) or None
    queries = bottle.request.params.queries or None

    service_url = "{}://{}".format(
        bottle.request.urlparts.scheme,
        bottle.request.urlparts.netloc,
    )

    # if we're doing a callback request then do that
    if bottle.request.query.callback:
        if bottle.request.query.query:
            bottle.response.content_type = "application/javascript"
            return "%s(%s)" % (bottle.request.query.callback, esdoc_orresponse(query, app))
        else:
            return "%s(%s)" % (bottle.request.query.callback, service_spec(app, service_url))

    # try fetching the query as json data or a string
    if bottle.request.query.query:
        return esdoc_orresponse(query, app)

    if queries:
        queries_json = json.loads(queries)
        queries_dict = json.loads(queries, object_pairs_hook=OrderedDict)
        # print(queries)
        results = {}
        counter = 0
        for query in queries_dict:
            query_id = "q" + str(counter)
            # print(queries_json[q], queries_json[q]["query"])
            result = esdoc_orresponse(recon_query(
                queries_json[query_id]["query"]), app)["result"]
            results.update({query_id: {"result": result}})
            counter += 1
        return results

    # otherwise just return the service specification
    return service_spec(app, service_url)


@app.route('/charity/<regno>')
@app.route('/charity/<regno>.<filetype>')
def charity(regno, filetype='html'):
    """
    Return a single charity record
    """

    regno_cleaned = clean_regno(regno)
    if regno_cleaned == "":
        return bottle.abort(404, bottle.template(
            'Charity {{regno}} not found.', regno=regno))

    res = app.config["es"].get(index=app.config["es_index"],
                               doc_type=app.config["es_type"], id=regno_cleaned, ignore=[404])
    if "_source" in res:
        if filetype == "html":
            return bottle.template('charity', charity=sort_out_date(res["_source"]), charity_id=res["_id"])
        return res["_source"]
    else:
        return bottle.abort(404, bottle.template('Charity {{regno}} not found.', regno=regno))


@app.route('/preview/charity/<regno>')
@app.route('/preview/charity/<regno>.html')
def charity_preview(regno):
    """
    Small version of charity record

    Used in reconciliation API
    """
    res = app.config["es"].get(index=app.config["es_index"], doc_type=app.config["es_type"], id=regno, ignore=[404])
    if "_source" in res:
        return bottle.template('preview', charity=sort_out_date(res["_source"]), charity_id=res["_id"], hide_title=("hide_title" in bottle.request.params))
    bottle.abort(404, bottle.template('Charity {{regno}} not found.', regno=regno))


@app.route('/orgid/<orgid>.json')
def orgid_json(orgid):
    """
    Fetch json representation based on a org-id for a record
    """

    # first try the charity records
    query = {
        "query": {
            "match": {
                "org-ids": {
                    "query": orgid,
                    "operator": "and",
                }
            }
        }
    }
    res = app.config["es"].search(index=app.config["es_index"],
                                  doc_type=app.config["es_type"],
                                  body=query,
                                  _source_exclude=["complete_names"],
                                  ignore=[404])
    if res.get("hits", {}).get("hits", []):
        org = res["hits"]["hits"][0]["_source"]
        org.update({"id": res["hits"]["hits"][0]["_id"]})
        return charity_to_org(org)

    # then look in the organisation records
    query["query"]["match"]["orgIDs"] = query["query"]["match"]["org-ids"]
    del query["query"]["match"]["org-ids"]
    res = app.config["es"].search(index=app.config["es_index"],
                                  doc_type="organisation",
                                  body=query,
                                  ignore=[404])
    if res.get("hits", {}).get("hits", []):
        org = res["hits"]["hits"][0]["_source"]
        org.update({"id": res["hits"]["hits"][0]["_id"]})
        return org

    bottle.abort(404, bottle.template(
        'Orgid {{orgid}} not found.', orgid=orgid))


def charity_to_org(record):
    org_types = ["Registered Charity"]
    if record.get("ccew_number"):
        org_types.append("Registered Charity (England and Wales)")
    if record.get("ccni_number"):
        org_types.append("Registered Charity (Northern Ireland)")
    if record.get("oscr_number"):
        org_types.append("Registered Charity (Scotland)")
    if record.get("company_number", []):
        org_types.append("Registered Company")

    return {
        "id": record.get("org-ids", [record.get("id")])[0],
        "name": record.get("known_as"),
        "charityNumber": record.get("id"),
        "companyNumber": record.get("company_number", [{}])[0].get("number") if record.get("company_number") else None,
        "streetAddress": None,
        "addressLocality": None,
        "addressRegion": None,
        "addressCountry": None,
        "postalCode": record.get("geo", {}).get("postcode"),
        "telephone": None,
        "alternateName": record.get("alt_names", []),
        "email": None,
        "description": None,
        "organisationType": org_types,
        "url": record.get("url"),
        "location": [],
        "dateModified": record.get("last_modified"),
        "latestIncome": record.get("latest_income"),
        "dateRegistered": record.get("date_registered"),
        "dateRemoved": record.get("date_removed"),
        "active": record.get("active"),
        "parent": record.get("parent"),
        "orgIDs": record.get("org-ids", []),
    }

EDU_SCOTLAND_LINKS = {
    "S12000033": "aberdeen-city",
    "S12000034": "aberdeenshire",
    "S12000041": "angus",
    "S12000035": "argyll-and-bute",
    "S12000005": "clackmannanshire",
    "S12000006": "dumfries-and-galloway",
    "S12000042": "dundee-city",
    "S12000008": "east-ayrshire",
    "S12000045": "east-dunbartonshire",
    "S12000010": "east-lothian",
    "S12000011": "east-renfrewshire",
    "S12000036": "edinburgh-city",
    "S12000014": "falkirk",
    "S12000015": "fife",
    "S12000046": "glasgow-city",
    "S12000017": "highland",
    "S12000018": "inverclyde",
    "S12000019": "midlothian",
    "S12000020": "moray",
    "S12000013": "eilean-siar-(western-isles)",
    "S12000021": "north-ayrshire",
    "S12000044": "north-lanarkshire",
    "S12000023": "orkney-islands",
    "S12000024": "perth-and-kinross",
    "S12000038": "renfrewshire",
    "S12000026": "scottish-borders",
    "S12000027": "shetland-islands",
    "S12000028": "south-ayrshire",
    "S12000029": "south-lanarkshire",
    "S12000030": "stirling",
    "S12000039": "west-dunbartonshire",
    "S12000040": "west-lothian",
}

def get_orgid_links(record):
    links = []
    for i in record["orgIDs"]:

        if i.startswith("GB-CHC-"):
            regno = i.replace("GB-CHC-", "")
            links.append({
                "url": "http://apps.charitycommission.gov.uk/Showcharity/RegisterOfCharities/SearchResultHandler.aspx?RegisteredCharityNumber={}&SubsidiaryNumber=0&Ref=CO".format(regno),
                "name":"Charity Commission England and Wales"
            })
            links.append({
                "url": "http://beta.charitycommission.gov.uk/charity-details/?regid={}&subid=0".format(regno),
                "name":"Charity Commission England and Wales (beta)"
            })
            links.append({
                "url": "https://charitybase.uk/charities/{}".format(regno),
                "name": "CharityBase"
            })
            links.append({
                "url": "http://opencharities.org/charities/{}".format(regno),
                "name":"OpenCharities"
            })
            links.append({
                "url": "http://www.guidestar.org.uk/summary.aspx?CCReg={}".format(regno),
                "name":"GuideStar"
            })
            links.append({
                "url": "http://www.charitychoice.co.uk/charities/search?t=qsearch&q={}".format(regno),
                "name":"Charities Direct"
            })
            links.append({
                "url": "https://olib.uk/charity/html/{}".format(regno),
                "name":"CharityData by Olly Benson"
            })

        elif i.startswith("GB-NIC-"):
            regno = i.replace("GB-NIC-", "")
            links.append({
                "url": "http://www.charitycommissionni.org.uk/charity-details/?regid={}&subid=0".format(regno), 
                "name":"Charity Commission Northern Ireland"
            })

        elif i.startswith("GB-SC-"):
            regno = i.replace("GB-SC-", "")
            links.append({
                "url": "https://www.oscr.org.uk/about-charities/search-the-register/charity-details?number={}".format(regno), 
                "name":"Office of the Scottish Charity Register"
            })

        elif i.startswith("GB-COH-"):
            regno = i.replace("GB-COH-", "")
            links.append({
                "url": "https://beta.companieshouse.gov.uk/company/{}".format(regno), 
                "name":"Companies House"
            })

        elif i.startswith("GB-EDU-"):
            regno = i.replace("GB-EDU-", "")
            links.append({
                "url": "https://get-information-schools.service.gov.uk/Establishments/Establishment/Details/{}".format(regno), 
                "name":"Get information about schools"
            })

        elif i.startswith("GB-SCOTEDU-"):
            regno = i.replace("GB-SCOTEDU-", "")
            la_slug = EDU_SCOTLAND_LINKS.get(record.get("location", [{}])[0].get("geoCode"))
            if la_slug:
                links.append({
                    "url": "https://education.gov.scot/parentzone/find-a-school/{}/{}".format(la_slug, regno),
                    "name": "Parentzone Scotland"
                })

        elif i.startswith("GB-NIEDU-"):
            regno = i.replace("GB-NIEDU-", "")
            links.append({
                "url": "http://apps.education-ni.gov.uk/appinstitutes/default.aspx",
                "name": "Department of Education - Institution Search (search for \"{}\")".format(regno)
            })

    return links

@app.route('/orgid/<orgid>')
@app.route('/orgid/<orgid>.html')
def orgid_html(orgid):
    """
    Redirect to a record based on the org-id
    """
    org = orgid_json(orgid)
    org["links"] = get_orgid_links(org)
    return bottle.template('org', org=sort_out_date(org))


@app.route('/feeds/ccew.<filetype>')
def ccew_rss(filetype):
    """
    Get an RSS feed based on when data is
    uploaded by the Charity Commission
    """
    ccew_url = 'http://data.charitycommission.gov.uk/'
    res = requests.get(ccew_url)
    soup = BeautifulSoup(res.text, 'html.parser')
    items = []
    for i in soup.find_all('blockquote'):
        links = i.find_all('a')
        idate = parser.parse(
            i.h4.string.split(", ")[1],
            default=datetime(2018, 1, 12, 0, 0)
        ).replace(tzinfo=timezone.utc)
        items.append({
            "name": i.h4.string,
            "date": idate,
            "link": links[0].get('href'),
            "author": "Charity Commission for England and Wales",
        })

    feed_contents = dict(
        items=items,
        title='Charity Commission for England and Wales data downloads',
        description='Downloads available from Charity Commission data downloads page.',
        url=ccew_url,
        feed_url=bottle.request.url,
        updated=datetime.now().replace(tzinfo=timezone.utc),
    )

    if filetype == 'atom':
        bottle.response.content_type = 'application/atom+xml'
        template = 'atom.xml'
    elif filetype == "json":
        bottle.response.content_type = 'application/json'
        return {
            "version": "https://jsonfeed.org/version/1",
            "title": feed_contents["title"],
            "home_page_url": feed_contents["url"],
            "feed_url": feed_contents["feed_url"],
            "description": feed_contents["description"],
            "items": [
                {
                    "id": item["link"],
                    "url": item["link"],
                    "title": item["name"],
                    "date_published": item["date"].isoformat(),
                } for item in items
            ]
        }
    else:
        bottle.response.content_type = 'application/rss+xml'
        template = 'rss.xml'

    return bottle.template(template, **feed_contents)


@app.route('/about')
def about():
    """About page
    """
    return bottle.template('about', this_year=datetime.now().year)


@app.route('/autocomplete')
def autocomplete():
    """
    Endpoint for autocomplete queries
    """
    search = bottle.request.params.q
    doc = {
        "suggest": {
            "suggest-1": {
                "prefix": search,
                "completion": {
                    "field": "complete_names",
                    "fuzzy" : {
                        "fuzziness" : 1
                    }
                }
            }
        }
    }
    res = app.config["es"].search(
        index=app.config["es_index"], doc_type="csv_data", body=doc,
        _source_include=['known_as'])
    return {"results": [
        {
            "label": x["_source"]["known_as"],
            "value": x["_id"]
        } for x in res.get("suggest", {}).get("suggest-1", [])[0]["options"]
    ]}


@app.route('/static/<filename:path>')
def send_static(filename):
    """ Fetch static files
    """
    return bottle.static_file(filename, root='static')


def sort_out_date(charity_record):
    """
    parse date fields in a charity record
    """
    date_fields = ["date_registered", "date_removed", "last_modified", 
                   "dateRegistered",  "dateRemoved",  "lastModified"]
    for date_field in date_fields:
        if charity_record.get(date_field):
            try:
                charity_record[date_field] = parser.parse(
                    charity_record[date_field])
            except ValueError:
                pass
    return charity_record

def clean_regno(regno):
    """
    Clean up a charity registration number
    """
    regno = str(regno)
    regno = regno.upper()
    regno = re.sub(r'^[^0-9SCNI]+|[^0-9]+$', '', regno)
    return regno


def main():
    """
    Run the server (command line version)
    """

    parser_args = argparse.ArgumentParser(description='')  # @TODO fill in

    # server options
    parser_args.add_argument('-host', '--host', default="localhost", help='host for the server')
    parser_args.add_argument('-p', '--port', default=8080, help='port for the server')
    parser_args.add_argument('--debug', action='store_true', dest="debug", help='Debug mode (autoreloads the server)')
    parser_args.add_argument('--server', default="auto", help='Server backend to use (see http://bottlepy.org/docs/dev/deployment.html#switching-the-server-backend)')

    # http auth
    parser_args.add_argument('--admin-password', help='Password for accessing admin pages')

    # elasticsearch options
    parser_args.add_argument('--es-host', default="localhost", help='host for the elasticsearch instance')
    parser_args.add_argument('--es-port', default=9200, help='port for the elasticsearch instance')
    parser_args.add_argument('--es-url-prefix', default='', help='Elasticsearch url prefix')
    parser_args.add_argument('--es-use-ssl', action='store_true', help='Use ssl to connect to elasticsearch')
    parser_args.add_argument('--es-index', default='charitysearch', help='index used to store charity data')
    parser_args.add_argument('--es-type', default='charity', help='type used to store charity data')

    parser_args.add_argument('--ga-tracking-id', help='Google Analytics Tracking ID')

    args = parser_args.parse_args()

    app.config["es"] = Elasticsearch(
        host=args.es_host,
        port=args.es_port,
        url_prefix=args.es_url_prefix,
        use_ssl=args.es_use_ssl
    )
    app.config["es_index"] = args.es_index
    app.config["es_type"] = args.es_type
    app.config["ga_tracking_id"] = args.ga_tracking_id
    app.config["admin_password"] = args.admin_password

    csv_app.config.update(app.config)
    bottle.debug(args.debug)

    if not app.config["es"].ping():
        raise ValueError("Elasticsearch connection failed")

    bottle.run(app, server=args.server, host=args.host, port=args.port, reloader=args.debug)

if __name__ == '__main__':
    main()
