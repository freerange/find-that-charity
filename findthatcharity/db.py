from elasticsearch import Elasticsearch

from . import settings
from .utils import sort_out_date

es = Elasticsearch(str(settings.ES_URL))

def fetch_all_sources():
    res = es.search(
        index="source",
        doc_type=settings.ES_TYPE,
        size=100,
        ignore=[404]
    )
    return {
        s["_id"]: sort_out_date(s["_source"], ["modified", "issued"]) for s in res["hits"]["hits"]
    }
