from collections import defaultdict, OrderedDict
from itertools import chain
import datetime
import logging
import math

import click
import sqlalchemy
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import tqdm

from findthatcharity import settings

priorities = [
    "GB-CHC",
    "GB-SC",
    "GB-NIC",
    "GB-COH",
    "GB-EDU"
]
priorities = {v: k+1 for k, v in enumerate(priorities[::-1])}

def get_complete_names(all_names):
    words = set()
    for n in all_names:
        if n:
            w = n.split()
            words.update([" ".join(w[r:]) for r in range(len(w))])
    return list(words)

def get_ids_from_record(record):
    if not isinstance(record, list):
        record = [record]
    ids_to_check = []
    for r in record:
        ids_to_check.extend([r["id"]] + r["linked_orgs"] + r["orgIDs"])
    return set([i for i in ids_to_check if i])

@click.group()
def cli():
    pass

@cli.command()
@click.option('--es-url', help='Elasticsearch connection', default=settings.ES_URL)
@click.option('--es-index', help='Elasticsearch type', default=settings.ES_INDEX)
@click.option('--es-type', help='Elasticsearch type', default=settings.ES_TYPE)
def create_index(es_url=settings.ES_URL,
               es_index=settings.ES_INDEX,
               es_type=settings.ES_TYPE):

    # connect to elasticsearch
    es = Elasticsearch(str(es_url))
    
    mapping = {
        "properties": {
            "geo": {
                "properties": {
                    "location": {
                        "type": "geo_point"
                    }
                }
            },
            "complete_names": {
                "type": "completion"
            }
        }
    }

    # create the index
    es.indices.create(index=es_index, ignore=400, body={
        "mappings": mapping
    })


@cli.command()
@click.option('--es-url', help='Elasticsearch connection', default=settings.ES_URL)
@click.option('--db-url', help='Database connection', default=settings.DB_URI)
@click.option('--es-index', help='Elasticsearch type', default=settings.ES_INDEX)
@click.option('--es-type', help='Elasticsearch type', default=settings.ES_TYPE)
@click.option('--es-bulk-limit', default=settings.ES_BULK_LIMIT, help='Bulk limit for importing data')
def importdata(es_url=settings.ES_URL, 
               db_url=settings.DB_URI,
               es_index=settings.ES_INDEX,
               es_type=settings.ES_TYPE,
               es_bulk_limit=settings.ES_BULK_LIMIT):
    """Import data from a database into an elasticsearch index"""
    
    # Connect to the data base
    engine = sqlalchemy.create_engine(str(db_url))
    conn = engine.connect()

    # connect to elasticsearch
    es_client = Elasticsearch(str(es_url))

    # create the linked_organisations view
    click.echo(f"Creating view...")
    create_view = """
    CREATE OR REPLACE VIEW linked_organisations
    AS SELECT organisation_links.organisation_id_a,
        organisation_links.organisation_id_b,
        organisation_links.description,
        organisation_links.source
    FROM organisation_links
    UNION ALL
    SELECT organisation_links.organisation_id_b AS organisation_id_a,
        organisation_links.organisation_id_a AS organisation_id_b,
        organisation_links.description,
        organisation_links.source
    FROM organisation_links;
    """
    conn.execute(create_view)
    click.echo(f"View created")

    # Fetch all the records
    click.echo(f"Fetching records...")
    sql = '''
    select o.*, 
        array_agg(l.organisation_id_b) as linked_orgs
    from organisation o 
        left outer join linked_organisations l
            on o.id = l.organisation_id_a
    group by o.id;
    '''
    results = conn.execute(sql)

    # get dictionary of organisations
    orgs_checked = set()
    orgs = defaultdict(list)
    for r in results:
        r = dict(r)
        ids = get_ids_from_record(r)
        for i in ids:
            orgs[i].append(r)

    click.echo(f"Loaded at least {len(orgs)} records from db")

    merged_orgs = []
    total_results = {
        "success": 0,
        "errors": []
    }
    last_updated = datetime.datetime.now()

    # create the merged organisation
    for k, v in tqdm.tqdm(orgs.items()):

        ids_to_check = get_ids_from_record(v)

        records = [orgs.get(i) for i in ids_to_check if orgs.get(i)]
        for r in records:
            ids_to_check.update(get_ids_from_record(r))
        records = [orgs.get(i) for i in ids_to_check if orgs.get(i)]
        records = [item for sublist in records for item in sublist]

        # if we've already found this organisation then ignore it and continue
        already_found = False
        for i in ids_to_check:
            if i in orgs_checked:
                already_found = True
        if already_found:
            continue

        orgs_checked.update(ids_to_check)

        ids = []
        for i in records:
            scheme = "-".join(i["id"].split("-")[0:2])
            priority = priorities.get(scheme, 0)
            if i["dateRegistered"] and i["active"]:
                age = (datetime.datetime.now().date() - i["dateRegistered"]).days
                priority += 1 / age
                
            ids.append((i["id"], scheme, priority, i["dateRegistered"], i["name"]))
            for j in i["linked_orgs"]:
                if j:
                    scheme = "-".join(j.split("-")[0:2])
                    priority = priorities.get(scheme, 0)
                    ids.append((j, scheme, priority, i["dateRegistered"], i["name"]))
            for j in i["orgIDs"]:
                if j:
                    scheme = "-".join(j.split("-")[0:2])
                    priority = priorities.get(scheme, 0)
                    ids.append((j, scheme, priority, i["dateRegistered"], i["name"]))
                
        ids = sorted(ids, key=lambda x: -x[2])
        orgids = list(OrderedDict.fromkeys([i[0] for i in ids]))
        names = list(OrderedDict.fromkeys([i[4] for i in ids]))
        alternateName = list(set(chain.from_iterable([[i["name"]] + i["alternateName"] for i in records])))
        
        merged_orgs.append({
            "_index": es_index,
            "_type": es_type,
            "_op_type": "index",
            "_id": orgids[0],
            "orgID": orgids[0],
            "name": names[0],
            "orgIDs": orgids,
            "alternateName": alternateName,
            "complete_names": {
                "input": get_complete_names(alternateName),
                "weight": max(1, math.ceil(math.log1p((i.get("latestIncome", 0) or 0))))
            },
            "organisationType": list(set(chain.from_iterable([i["organisationType"] for i in records]))),
            "sources": list(set([i["source"] for i in records])),
            "active": len([i["active"] for i in records if i["active"]]) > 0,
            "postalCode": list(set([i["postalCode"] for i in records if i["postalCode"]])),
            "last_updated": last_updated,
            # "records": records,
        })

        if len(merged_orgs) >= es_bulk_limit:
            results = bulk(
                es_client,
                merged_orgs,
                raise_on_error=False,
                chunk_size=es_bulk_limit,
                request_timeout=600,
            )
            total_results["success"] += results[0]
            total_results["errors"].extend(results[1])
            merged_orgs = []
            
    results = bulk(
        es_client,
        merged_orgs,
        raise_on_error=False,
        chunk_size=es_bulk_limit,
        request_timeout=600,
    )
    total_results["success"] += results[0]
    total_results["errors"].extend(results[1])
    merged_orgs = []

    click.echo('{:,.0f} organisations saved to elasticsearch'.format(total_results['success']))
    if total_results["errors"]:
        click.echo('{:,.0f} errors while saving. Showing first 5 errors'.format(len(total_results['errors'])))
        for k, e in enumerate(total_results["errors"]):
            click.echo(e)
            if k > 4:
                break

    q = {
        "query": {
            "bool" : {
                "must_not" : {
                        "match": {
                            "last_updated": last_updated
                        }
                    }
                }
            }
        }
    result = es_client.delete_by_query(index=es_index, body=q, conflicts='proceed', timeout='30m')
    click.echo('Removed {:,.0f} old records'.format(result['deleted']))

if __name__ == '__main__':
    cli()
