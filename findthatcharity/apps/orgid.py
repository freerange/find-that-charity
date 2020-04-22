from datetime import datetime
import io
import csv

from starlette.routing import Route
from starlette.responses import RedirectResponse, Response
from elasticsearch.helpers import scan

from ..queries import orgid_query, random_query, search_query
from ..db import es, ORGTYPES, db_con, organisation
from .. import settings
from ..utils import JSONResponseDate as JSONResponse, pagination, pagination_request
from ..templates import templates
from ..classes.org import OrgRecord, Org


async def orgid_type_download(request):
    base_orgtype = [
        ORGTYPES.get(o, {}).get("key", o)
        for o in request.path_params.get('orgtype', "").split("+")
        if o
    ]
    query_orgtypes = [
        ORGTYPES.get(o, {}).get("key", o)
        for o in request.query_params.getlist('orgtype')
        if o
    ]
    base_source = [o for o in request.path_params.get('source', "").split("+") if o]
    q = request.query_params.get('q')
    active = not request.query_params.get('inactive')

    query = search_query(
        term=q,
        base_orgtype=base_orgtype,
        base_source=base_source,
        orgtype=query_orgtypes,
        source=request.query_params.getlist('source'),
        active=active,
        aggregate=True,
        size=1000,
    )
    res = es.search_template(
        index=settings.ES_INDEX,
        doc_type=settings.ES_TYPE,
        body=query,
        ignore=[404],
        scroll='5m',
    )
    scroll_id = res.get('_scroll_id')
    output = io.StringIO()
    writer = csv.writer(output)
    fields = [
        "orgID",
        "name",
        "active",
        "postalCode",
        "orgIDs",
        "alternateName",
    ]
    writer.writerow(fields)
    while len(res['hits']['hits']):
        for o in res.get("hits", {}).get("hits", []):
            writer.writerow([
                o["_source"].get(f)
                for f in fields
            ])
        res = es.scroll(
            scroll_id=scroll_id,
            scroll='5m',
        )
    return Response(output.getvalue(), media_type='text/csv')


async def orgid_type(request):
    base_orgtype = [
        ORGTYPES.get(o, {}).get("key", o)
        for o in request.path_params.get('orgtype', "").split("+")
        if o
    ]
    query_orgtypes = [
        ORGTYPES.get(o, {}).get("key", o)
        for o in request.query_params.getlist('orgtype')
        if o
    ]
    base_source = [o for o in request.path_params.get('source', "").split("+") if o]
    q = request.query_params.get('q')
    p = pagination_request(request, defaultsize=10)
    active = not request.query_params.get('inactive')

    query = search_query(
        term=q,
        base_orgtype=base_orgtype,
        base_source=base_source,
        orgtype=query_orgtypes,
        source=request.query_params.getlist('source'),
        active=active,
        aggregate=True,
        p=p['p'],
        size=p['size'],
    )
    res = es.search_template(
        index=settings.ES_INDEX,
        doc_type=settings.ES_TYPE,
        body=query,
        ignore=[404],
    )

    download_url = request.url.replace(path=request.url.path + '.csv')

    return templates.TemplateResponse('orgtype.html', {
        'term': q,
        'request': request,
        'res': {
            "hits": [Org(o["_id"], **o["_source"]) for o in res.get("hits", {}).get("hits", [])],
            "total": res.get("hits", {}).get("total"),
        },
        'query': base_orgtype + [
            templates.env.globals["sources"].get(s, {"publisher": {"name": s}}).get("publisher", {}).get("name", s)
            for s in base_source
        ],
        'aggs': res["aggregations"],
        'pages': pagination(p["p"], p["size"], res.get("hits", {}).get("total")),
        'download_url': download_url,
    })


async def orgid_json(request):
    """
    Fetch json representation based on a org-id for a record
    """
    orgid = request.path_params['orgid']
    orgs = get_orgs_from_orgid(orgid)
    if orgs:
        return JSONResponse(orgs)
    return JSONResponse({
        "error": 'Orgid {} not found.'.format(orgid),
        "query": {"orgid": orgid}
    }, 404)


async def orgid_html(request):
    """
    Find a record based on the org-id
    """
    orgid = request.path_params['orgid']

    template = 'org.html'
    if orgid.endswith("/preview"):
        orgid = orgid[:-8]
        template = 'org_preview.html'

    org = Org.from_es(orgid, es, settings.ES_INDEX, settings.ES_TYPE)
    if org:
        org.fetch_records(db_con, organisation)
        org.fetch_org_links(db_con)
        return templates.TemplateResponse(template, {
            'request': request,
            'org': org,
            'key_types': settings.KEY_TYPES,
            # 'parent_orgs': get_parents(orgs),
            # 'child_orgs': get_children(orgs),
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
        _source_excludes=["complete_names"],
        ignore=[404]
    )

    orgids = set()
    if res.get("hits", {}).get("hits", []):
        o = res["hits"]["hits"][0]
        o = Org(o["_id"], o["_source"])
        return MergedOrg(o)

def get_parents(orgs):
    parents = {}
    for k, v in orgs.data["parent"].items():
        if v["value"] not in parents:
            parents[v["value"]] = get_orgs_from_orgid(v["value"])
    return parents

def get_children(orgs):
    children = {}

    res = es.search(
        index=settings.ES_INDEX,
        doc_type=settings.ES_TYPE,
        body={
            "query": {
                "terms": {
                    "parent.keyword": [v["value"] for v in orgs.data["orgIDs"].values()]
                }
            }
        },
        _source_excludes=["complete_names"],
        ignore=[404]
    )

    for o in res.get("hits", {}).get("hits", []):
        if o["_id"] not in children:
            children[o["_id"]] = Org(o["_id"], o["_source"])

    return list(children.values())

routes = [
    Route('/type/{orgtype}.csv', orgid_type_download),
    Route('/type/{orgtype}.html', orgid_type),
    Route('/type/{orgtype}', orgid_type, name='orgid_type'),
    Route('/source/{source}.csv', orgid_type_download),
    Route('/source/{source}.html', orgid_type),
    Route('/source/{source}', orgid_type, name='orgid_source'),
    Route('/{orgid}.json', orgid_json),
    Route('/{orgid:path}.html', orgid_html),
    Route('/{orgid:path}', orgid_html, name='orgid_html'),
]
