from collections import Counter

from elasticsearch import Elasticsearch
from sqlalchemy import create_engine, MetaData, Table, Column, String, Text, BigInteger, DateTime, JSON, Date, Boolean

from . import settings
from .utils import sort_out_date

es = Elasticsearch(str(settings.ES_URL))

if not es.ping():
    raise ValueError("Elasticsearch connection failed for {}".format(str(settings.ES_URL)))

db = create_engine(str(settings.DB_URL))
db_con = db.connect()
metadata = MetaData()

def fetch_all_sources():
    res = es.search(
        index="source",
        doc_type=settings.ES_TYPE,
        size=100,
        ignore=[404]
    )
    
    def check_duplicate_publishers(sources):
        publishers = Counter([s.get("publisher", {}).get("name") for s in sources.values()])
        for i, s in sources.items():
            sources[i]["publisher"]["duplicate"] = publishers[s.get("publisher", {}).get("name")]>1
        return sources

    return check_duplicate_publishers({
        s["_id"]: sort_out_date(s["_source"], ["modified", "issued"]) for s in res.get("hits", {}).get("hits", [])
    })

def get_org_types():
    res = es.search(index=settings.ES_INDEX,
                    doc_type=settings.ES_TYPE,
                    _source=False,
                    size=0,
                    body={
                        "aggs": {
                            "org_types": {
                                "terms": {
                                    "field": "organisationType.keyword",
                                    "size": 500
                                }
                            }
                        }
                    }
                    )
    return {
        r["key"]: r["doc_count"] for r in
        res["aggregations"]["org_types"]["buckets"]
    }


def value_counts():
    res = es.search(
        index=settings.ES_INDEX,
        doc_type=settings.ES_TYPE,
        size=0,
        body={
            "query": {
                "match": {
                    "active": True
                }
            },
            "aggs" : {
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
        },
        ignore=[404]
    )
    return res.get("aggregations", {})

organisation = Table('organisation', metadata, 
    Column("id", String, primary_key=True),
    Column("name", String),
    Column("charityNumber", String),
    Column("companyNumber", String),
    Column("addressLocality", String),
    Column("addressRegion", String),
    Column("addressCountry", String),
    Column("postalCode", String),
    Column("telephone", String),
    Column("email", String),
    Column("description", Text),
    Column("url", String),
    Column("latestIncome", BigInteger),
    Column("latestIncomeDate", Date),
    Column("dateRegistered", Date),
    Column("dateRemoved", Date),
    Column("active", Boolean),
    Column("status", String),
    Column("parent", String),
    Column("dateModified", DateTime),
    Column("location", JSON),
    Column("orgIDs", JSON),
    Column("alternateName", JSON),
    Column("organisationType", JSON),
    Column("organisationTypePrimary", String),
    Column("source", String),
)
