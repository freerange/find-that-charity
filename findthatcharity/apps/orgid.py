from datetime import datetime
import io
import csv

from starlette.routing import Route
from starlette.responses import RedirectResponse, Response
from elasticsearch.helpers import scan
import sqlalchemy

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
    query_source = request.query_params.getlist('source')
    q = request.query_params.get('q')
    limit = request.query_params.get('limit')
    limit = int(limit) if (limit and limit.isdigit()) else None
    active = not request.query_params.get('inactive')

    whereclause = []
    if active:
        whereclause.append(organisation.c.active==True)
    for o in base_orgtype:
        whereclause.append(organisation.c.organisationType.comparator.contains([o]))
    if query_orgtypes:
        whereclause.append(
            sqlalchemy.and_(*[organisation.c.organisationType.comparator.contains([o]) for o in query_orgtypes])
        )
    if (base_source + query_source):
        whereclause.append(
            sqlalchemy.and_(*[organisation.c.source==o for o in base_source + query_source])
        )
    whereclause = sqlalchemy.and_(*whereclause) if whereclause else None

    query = sqlalchemy.select(
        columns=[
            organisation.c.id,
            organisation.c.name,
            organisation.c.charityNumber,
            organisation.c.companyNumber,
            # organisation.c.addressLocality,
            # organisation.c.addressRegion,
            # organisation.c.addressCountry,
            organisation.c.postalCode,
            # organisation.c.telephone,
            # organisation.c.email,
            # organisation.c.description,
            organisation.c.url,
            organisation.c.latestIncome,
            organisation.c.latestIncomeDate,
            organisation.c.dateRegistered,
            organisation.c.dateRemoved,
            organisation.c.active,
            # organisation.c.status,
            # organisation.c.parent,
            organisation.c.dateModified,
            # organisation.c.location,
            organisation.c.orgIDs,
            # organisation.c.alternateName,
            organisation.c.organisationType,
            # organisation.c.organisationTypePrimary,
            organisation.c.source,
        ],
        limit=limit,
        order_by=organisation.c.id,
        whereclause=whereclause,
    )
    res = db_con.execute(query)

    # query = search_query(
    #     term=q,
    #     base_orgtype=base_orgtype,
    #     base_source=base_source,
    #     orgtype=query_orgtypes,
    #     source=request.query_params.getlist('source'),
    #     active=active,
    #     aggregate=True,
    #     size=1000,
    # )
    # res = es.search_template(
    #     index=settings.ES_INDEX,
    #     doc_type=settings.ES_TYPE,
    #     body=query,
    #     ignore=[404],
    #     scroll='5m',
    # )
    # scroll_id = res.get('_scroll_id')
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(list(res.keys()))
    for r in res:
        writer.writerow(r)
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

    download_url = request.url.replace(path=request.url.path.replace(".html", '') + '.csv')

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


async def get_orgid_by_hash(request):
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
    Route('/hash/{hash}', get_orgid_by_hash, name='get_orgid_by_hash'),
]
