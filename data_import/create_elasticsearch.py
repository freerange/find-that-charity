import argparse
from elasticsearch import Elasticsearch
import os


INDEXES = [
    {
        "name": "charitysearch",
        "mapping": {
            "organisation": {
                "properties": {
                    "complete_names": {
                        "type": "completion",
                        "contexts": [
                            {
                                "name": "organisationType",
                                "type": "category",
                                "path": "organisationType"
                            }
                        ]
                    }
                }
            }
        }
    }
]


def main():

    parser = argparse.ArgumentParser(description='Setup elasticsearch indexes.')
    parser.add_argument('--reset', action='store_true',
                        help='If set, any existing indexes will be deleted and recreated (data will be lost).')
    parser.add_argument('--reindex', action='store_true',
                        help='If set, any existing indexes will be deleted and recreated (keeping the data).')

    # elasticsearch options
    parser.add_argument('--es-host', default="localhost", help='host for the elasticsearch instance')
    parser.add_argument('--es-port', default=9200, help='port for the elasticsearch instance')
    parser.add_argument('--es-url-prefix', default='', help='Elasticsearch url prefix')
    parser.add_argument('--es-use-ssl', action='store_true', help='Use ssl to connect to elasticsearch')
    parser.add_argument('--es-index', default='charitysearch', help='index used to store charity data')

    args = parser.parse_args()
    if args.reindex:
        args.reset = True

    es = Elasticsearch(host=args.es_host, port=args.es_port, url_prefix=args.es_url_prefix, use_ssl=args.es_use_ssl)

    potential_env_vars = [
        "ELASTICSEARCH_URL",
        "ES_URL",
        "BONSAI_URL"
    ]
    for e_v in potential_env_vars:
        if os.environ.get(e_v):
            es = Elasticsearch(os.environ.get(e_v))
            break

    INDEXES[0]["name"] = args.es_index
    temp_index = "tempindex"

    for i in INDEXES:
        if es.indices.exists(i["name"]):
            if args.reindex:
                print("[elasticsearch] copying '%s' index to temporary index '%s'" % (i["name"], temp_index))
                res = es.reindex(body={
                    "source": {
                        "index": i["name"]
                    },
                    "dest": {
                        "index": temp_index,
                        "version_type": "external"
                    }
                })
                print("[elasticsearch] response: '%s'" % (res))
        
            if args.reset:
                print("[elasticsearch] deleting '%s' index..." % (i["name"]))
                res = es.indices.delete(index=i["name"])
                print("[elasticsearch] response: '%s'" % (res))

        if not es.indices.exists(i["name"]):
            print("[elasticsearch] creating '%s' index..." % (i["name"]))
            res = es.indices.create(index=i["name"])

        if "mapping" in i:
            for es_type, mapping in i["mapping"].items():
                res = es.indices.put_mapping(es_type, mapping, index=i["name"])
                print("[elasticsearch] set mapping on {} index (type: {})".format(i["name"], es_type))

        if args.reindex and es.indices.exists(temp_index):
                print("[elasticsearch] copying '%s' index to temporary index '%s'" % (
                    temp_index, i["name"]))
                res = es.reindex(body={
                    "source": {
                        "index": temp_index
                    },
                    "dest": {
                        "index": i["name"],
                        "version_type": "external"
                    }
                })
                print("[elasticsearch] response: '%s'" % (res))
                print("[elasticsearch] deleting temporary '%s' index..." % (temp_index))
                res = es.indices.delete(index=temp_index)
                print("[elasticsearch] response: '%s'" % (res))


if __name__ == '__main__':
    main()
