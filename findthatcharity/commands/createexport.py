import csv
import gzip

import click
import sqlalchemy
from elasticsearch import Elasticsearch

from findthatcharity import settings
from findthatcharity.db import organisation
from findthatcharity.classes.org import Org

@click.group()
def cli():
    pass

@cli.command()
@click.option('--outfile', help="File to output", default=settings.OUTPUT_DOWNLOAD)
@click.option('--es-url', help='Elasticsearch connection', default=settings.ES_URL)
@click.option('--db-url', help='Database connection', default=settings.DB_URI)
@click.option('--es-index', help='Elasticsearch type', default=settings.ES_INDEX)
@click.option('--es-type', help='Elasticsearch type', default=settings.ES_TYPE)
@click.option('--gzip/--no-gzip', 'usegzip', help='Whether to GZIP the result', default=True)
@click.option('--limit', help='Limit the number of rows output', default=None, type=int)
def export_data(outfile,
               es_url=settings.ES_URL, 
               db_url=settings.DB_URI,
               es_index=settings.ES_INDEX,
               es_type=settings.ES_TYPE,
               usegzip=True,
               limit=None):
    """Create a CSV file with all the data in"""
    
    # Connect to the data base
    engine = sqlalchemy.create_engine(str(db_url))
    conn = engine.connect()

    # connect to elasticsearch
    es_client = Elasticsearch(str(es_url))

    # create the linked_organisations view
    click.echo(f"Fetch all organisation")
    result = conn.execute(
        organisation.select(limit=limit, order_by=organisation.c.id)
    )

    fields = list(result.keys()) + ['canonical_orgid']
    
    # create the output file
    if usegzip:
        click.echo(f"Create output file (gzipped)")
        f = gzip.open(outfile, 'wt', newline='', encoding='utf8')
    else:
        click.echo(f"Create output file")
        f = open(outfile, 'w', newline='', encoding='utf8')
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    for r in result:
        r = dict(r)
        canon = Org.from_es(r['id'], es_client, es_index)
        # canon = False
        if canon:
            r['canonical_orgid'] = canon.id
        else:
            r['canonical_orgid'] = r['id']
        writer.writerow(r)
    click.echo(f"Output file created")
