import argparse
import os
import csv
from datetime import datetime

from elasticsearch import Elasticsearch

from import_charities import save_to_elasticsearch

AREA_TYPES = {
    "E00": "OA",
    "E01": "LSOA",
    "E02": "MSOA",
    "E04": "PAR",
    "E05": "WD",
    "E06": "UA",
    "E07": "NMD",
    "E08": "MD",
    "E09": "LONB",
    "E10": "CTY",
    "E12": "RGN/GOR",
    "E14": "WPC",
    "E15": "EER",
    "E21": "CANNET",
    "E22": "CSP",
    "E23": "PFA",
    "E25": "PUA",
    "E26": "NPARK",
    "E28": "REGD",
    "E29": "REGSD",
    "E30": "TTWA",
    "E31": "FRA",
    "E32": "LAC",
    "E33": "WZ",
    "E36": "CMWD",
    "E37": "LEP",
    "E38": "CCG",
    "E39": "NHSAT",
    "E41": "CMLAD",
    "E42": "CMCTY",
    "N00": "SA",
    "N06": "WPC",
    "S00": "OA",
    "S01": "DZ",
    "S02": "IG",
    "S03": "CHP",
    "S05": "ROA - CPP",
    "S06": "ROA - Local",
    "S08": "HB",
    "S12": "CA",
    "S13": "WD",
    "S14": "WPC",
    "S16": "SPC",
    "S22": "TTWA",
    "W00": "OA",
    "W01": "LSOA",
    "W02": "MSOA",
    "W03": "USOA",
    "W04": "COM",
    "W05": "WD",
    "W06": "UA",
    "W07": "WPC",
    "W09": "NAWC",
    "W14": "CDRP",
    "W20": "REGD",
    "W21": "REGSD",
    "W22": "TTWA",
    "W30": "AgricSmall",
    "W33": "CFA",
    "W35": "WZ",
    "W39": "CMWD",
    "W40": "CMLAD",
    "W41": "CMCTY",
}

REGION_CONVERT = {
    "A": "E12000001",
    "B": "E12000002",
    "D": "E12000003",
    "E": "E12000004",
    "F": "E12000005",
    "G": "E12000006",
    "H": "E12000007",
    "J": "E12000008",
    "K": "E12000009",
}

def import_gias(orgs,
                datafile=os.path.join("data", "gias_england.csv"),
                es_index="charitysearch",
                es_type="organisation",
                debug=False):
    with open(datafile) as a:
        csvreader = csv.DictReader(a)
        rcount = 0
        for row in csvreader:
            row = clean_gias(row)
            row["_index"] = es_index
            row["_type"] = es_type
            row["_op_type"] = "index"
            orgs[row["_id"]] = row
            rcount += 1
            if rcount % 10000 == 0:
                print('\r', "[GIAS] {} organisations added or updated from {}".format(rcount, datafile), end='')
            if debug and rcount > 500:
                break
    print('\r', "[GIAS] {} organisations added or updated from {}".format(rcount, datafile))

    return orgs

def clean_gias(record):

    # clean blank values
    for f in record.keys():
        if record[f] == "":
            record[f] = None

    # dates
    date_fields = ["OpenDate", "CloseDate"]
    for f in date_fields:
        try:
            if record.get(f):
                record[f] = datetime.strptime(record.get(f), "%d-%m-%Y")
        except ValueError:
            record[f] = None

    # org ids:
    org_ids = ["GB-EDU-{}".format(record.get("URN"))]
    if record.get("UKPRN"):
        org_ids.append("GB-UKPRN-{}".format(record.get("UKPRN")))
    if record.get("EstablishmentNumber") and record.get("LA (code)"):
        org_ids.append("GB-LAESTAB-{}/{}".format(
            record.get("LA (code)").rjust(3, "0"),
            record.get("EstablishmentNumber").rjust(4, "0"),
        ))

    return {
        "_id": "GB-EDU-{}".format(record.get("URN")),
        "name": record.get("EstablishmentName"),
        "department": None,
        "contactName": None,
        "charityNumber": None,
        "companyNumber": None,
        "streetAddress": record.get("Street"),
        "addressLocality": record.get("Locality"),
        "addressRegion": record.get("Address3"),
        "addressCountry": record.get("Country (name)"),
        "postalCode": record.get("Postcode"),
        "telephone": record.get("TelephoneNum"),
        "alternateName": None,
        "email": None,
        "description": None,
        "organisationType": [
            "Education",
            record.get("EstablishmentTypeGroup (name)"),
            record.get("TypeOfEstablishment (name)"),
        ],
        "url": record.get("SchoolWebsite"),
        "location": get_locations(record),
        "dateModified": None,
        "dateRegistered": record.get("OpenDate"),
        "dateRemoved": record.get("CloseDate"),
        "active": record.get("EstablishmentStatus (name)") != "Closed",
        "parent": record.get("PropsName"),
        "orgIDs": org_ids,
    }

def get_locations(record):
    location_fields = ["GOR", "DistrictAdministrative", "AdministrativeWard",
                       "ParliamentaryConstituency", "UrbanRural", "MSOA", "LSOA"]
    locations = []
    for f in location_fields:
        code = record.get(f+" (code)", "")
        name = record.get(f+" (name)", "")

        if name == "" and code == "":
            continue

        if f == "GOR":
            code = REGION_CONVERT.get(code, code)

        if code == "":
            code = name

        locations.append({
            "id": code,
            "name": record.get(f+" (name)"),
            "geoCode": code,
            "geoCodeType": AREA_TYPES.get(code[0:3], f),
        })

    return locations


def main():

    parser = argparse.ArgumentParser(description='Import education data into elasticsearch')

    parser.add_argument('--folder', type=str, default='data',
                        help='Root path of the data folder.')

    # elasticsearch options
    parser.add_argument('--es-host', default="localhost", help='host for the elasticsearch instance')
    parser.add_argument('--es-port', default=9200, help='port for the elasticsearch instance')
    parser.add_argument('--es-url-prefix', default='', help='Elasticsearch url prefix')
    parser.add_argument('--es-use-ssl', action='store_true', help='Use ssl to connect to elasticsearch')
    parser.add_argument('--es-index', default='charitysearch', help='index used to store charity data')
    parser.add_argument('--es-type', default='organisation', help='type used to store organisation data')

    parser.add_argument('--skip-gias', action='store_true',
                        help='Don\'t fetch data from English schools list.')

    parser.add_argument('--debug', action='store_true', help='')

    args = parser.parse_args()

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

    if not es.ping():
        raise ValueError("Elasticsearch connection failed")

    data_files = {
        "gias": os.path.join(args.folder, "gias_england.csv"),
    }

    orgs = {}
    if not args.skip_gias:
        orgs = import_gias(orgs, datafile=data_files["gias"], es_index=args.es_index, es_type=args.es_type, debug=args.debug)

    if args.debug:
        import random
        random_keys = random.choices(list(orgs.keys()), k=10)
        for r in random_keys:
            print(r, orgs[r])

    save_to_elasticsearch(orgs, es, args.es_index)

if __name__ == '__main__':
    main()
