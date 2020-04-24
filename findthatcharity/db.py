from collections import Counter

from elasticsearch import Elasticsearch
from sqlalchemy import create_engine, MetaData, Table, Column, String, Text, BigInteger, Integer, DateTime, Date, Boolean, select
from sqlalchemy.dialects.postgresql import JSONB

from . import settings
from .utils import sort_out_date, sort_out_orgtypes

es = Elasticsearch(str(settings.ES_URL))

if not es.ping():
    raise ValueError("Elasticsearch connection failed for {}".format(str(settings.ES_URL)))

db = create_engine(str(settings.DB_URI))
db_con = db.connect()
metadata = MetaData()


def fetch_all_sources():

    def sort_source(source):
        source = dict(source)
        source['publisher'] = {
            "name": source["publisher_name"],
            "website": source["publisher_website"],
        }
        del source["publisher_name"]
        del source["publisher_website"]
        return source

    return {s["identifier"]: sort_source(s) for s in db_con.execute(select([source])).fetchall()}

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
                },
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


vals = value_counts()
ORGTYPES = sort_out_orgtypes(vals.get("group_by_type", {}).get("buckets",[]))
SOURCES = vals.get("group_by_source", {}).get("buckets", [])


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
    Column("location", JSONB),
    Column("orgIDs", JSONB),
    Column("alternateName", JSONB),
    Column("organisationType", JSONB),
    Column("organisationTypePrimary", String),
    Column("source", String),
)

source = Table('source', metadata,
    Column("identifier", String, primary_key = True),
    Column("title", String),
    Column("description", Text),
    Column("license", String),
    Column("license_name", String),
    Column("issued", DateTime),
    Column("modified", DateTime),
    Column("publisher_name", String),
    Column("publisher_website", String),
    Column("distribution", JSONB),
)

organisation_links = Table('organisation_links', metadata,
    Column("organisation_id_a", String, primary_key = True),
    Column('organisation_id_b', String, primary_key = True),
    Column('description', String),
    Column('source', String),
)


identifier = Table('identifier', metadata,
    Column("code", String, primary_key = True),
    Column("description_en", String),
    Column("License", String),
    Column("access_availableOnline", Boolean),
    Column("access_exampleIdentifiers", String),
    Column("access_guidanceOnLocatingIds", String),
    Column("access_languages", String),
    Column("access_onlineAccessDetails", String),
    Column("access_publicDatabase", String),
    Column("confirmed", Boolean),
    Column("coverage", String),
    Column("data_availability", String),
    Column("data_dataAccessDetails", String),
    Column("data_features", String),
    Column("data_licenseDetails", String),
    Column("data_licenseStatus", String),
    Column("deprecated", Boolean),
    Column("formerPrefixes", String),
    Column("links_opencorporates", String),
    Column("links_wikipedia", String),
    Column("listType", String),
    Column("meta_lastUpdated", Date),
    Column("meta_source", String),
    Column("name_en", String),
    Column("name_local", String),
    Column("quality", Integer),
    Column("quality_explained_Availability_API", Integer),
    Column("quality_explained_Availability_BulkDownload", Integer),
    Column("quality_explained_Availability_CSVFormat", Integer),
    Column("quality_explained_Availability_ExcelFormat", Integer),
    Column("quality_explained_Availability_JSONFormat", Integer),
    Column("quality_explained_Availability_PDFFormat", Integer),
    Column("quality_explained_Availability_RDFFormat", Integer),
    Column("quality_explained_Availability_XMLFormat", Integer),
    Column("quality_explained_License_ClosedLicense", Integer),
    Column("quality_explained_License_NoLicense", Integer),
    Column("quality_explained_License_OpenLicense", Integer),
    Column("quality_explained_ListType_Local", Integer),
    Column("quality_explained_ListType_Primary", Integer),
    Column("quality_explained_ListType_Secondary", Integer),
    Column("quality_explained_ListType_ThirdParty", Integer),
    Column("registerType", String),
    Column("sector", String),
    Column("structure", String),
    Column("subnationalCoverage", String),
    Column("url", String),
)

scrape = Table('scrape', metadata,
    Column("id", String, primary_key=True),
    Column("spider", String),
    Column("stats", String),
    Column("finish_reason", String),
    Column("items", Integer),
    Column("errors", Integer),
    Column("start_time", DateTime),
    Column("finish_time", DateTime),
)
