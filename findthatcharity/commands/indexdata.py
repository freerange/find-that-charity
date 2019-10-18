from collections import defaultdict, OrderedDict
from itertools import chain
import datetime
import logging
import math

import click
import sqlalchemy
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk


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

@click.command()
@click.option('--es-url', help='Elasticsearch connection')
@click.option('--db-url', help='Database connection')
@click.option('--es-bulk-limit', default=500, help='Bulk limit for importing data')
def importdata(es_url, db_url, es_bulk_limit):
    """Import data from a database into an elasticsearch index"""
    
    # Connect to the data base
    engine = sqlalchemy.create_engine(db_url)
    conn = engine.connect()

    # connect to elasticsearch
    es_client = Elasticsearch(es_url)

    # Fetch all the records
    sql = '''
    select o.*, 
        array_agg(l.organisation_id_b) as linked_orgs
    from organisation o 
        left outer join linked_organisations l
            on o.id = l.organisation_id_a
    group by o.id;
    '''
    results = conn.execute(sql)

    # group by linked organisations
    orgs = defaultdict(list)
    for k, r in enumerate(results):
        
        for i in r.linked_orgs:
            if i in orgs.keys():
                orgs[i].append(dict(r))
                continue
        
        orgs[r.id].append(dict(r))

    click.echo(f"Loaded at least {len(orgs)} records from db")

    merged_orgs = []

    # create the merged organisation
    for k, v in orgs.items():
        ids = []
        for i in v:
            scheme = "-".join(i["id"].split("-")[0:2])
            priority = priorities.get(scheme, 0)
            if i["dateRegistered"]:
                age = (datetime.datetime.now().date() - i["dateRegistered"]).days
                priority += 1 / age
                
            ids.append((i["id"], scheme, priority, i["dateRegistered"], i["name"]))
            for j in i["linked_orgs"]:
                if j:
                    scheme = "-".join(j.split("-")[0:2])
                    priority = priorities.get(scheme, 0)
                    ids.append((j, scheme, priority, i["dateRegistered"], i["name"]))
                
        ids = sorted(ids, key=lambda x: -x[2])
        orgids = list(OrderedDict.fromkeys([i[0] for i in ids]))
        names = list(OrderedDict.fromkeys([i[4] for i in ids]))
        alternateName = list(set(chain.from_iterable([[i["name"]] + i["alternateName"] for i in v])))
        
        merged_orgs.append({
            "_index": "organisation",
            "_type": "item",
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
            "organisationType": list(set(chain.from_iterable([i["organisationType"] for i in v]))),
            "postalCode": list(set([i["postalCode"] for i in v if i["postalCode"]])),
            # "records": {i["id"]: i for i in v},
        })

        if len(merged_orgs) >= es_bulk_limit:
            results = bulk(es_client, merged_orgs, raise_on_error=False, chunk_size=es_bulk_limit)
            click.echo(f"[elasticsearch] saved {results[0]} records")
            merged_orgs = []
            
    results = bulk(es_client, merged_orgs, raise_on_error=False, chunk_size=es_bulk_limit)
    click.echo(f"[elasticsearch] saved {results[0]} records")
    merged_orgs = []

if __name__ == '__main__':
    importdata()