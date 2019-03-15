from elasticsearch import Elasticsearch

from . import settings

es = Elasticsearch(str(settings.ES_URL))