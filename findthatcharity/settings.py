from starlette.config import Config
from starlette.datastructures import URL, Secret

config = Config(".env")

DEBUG = config('DEBUG', cast=bool, default=False)
TESTING = config('TESTING', cast=bool, default=False)

ES_URL = config('ES_URL', cast=URL, default='http://localhost:9200')
if TESTING:
    ES_URL = ES_URL.replace(database='test_' + ES_URL.database)
ES_INDEX = config('ES_INDEX', default='organisation')
ES_TYPE = config('ES_TYPE', default='_doc')
ES_BULK_LIMIT = config('ES_BULK_LIMIT', cast=int, default=500)

DB_URI = config('DB_URI', cast=URL)

ORGID_JSON = config('ORGID_JSON', default='http://org-id.guide/download.json')

# key organisation types to highlight
KEY_TYPES = [
    # "Registered Charity",
    "Registered Charity (England and Wales)",
    "Registered Charity (Scotland)",
    "Registered Charity (Northern Ireland)",
    "Registered Company",
    # "Company Limited by Guarantee",
    "Charitable Incorporated Organisation",
    "Education",
    "Community Interest Company",
    "Health",
    "Registered Society",
    "Community Amateur Sports Club",
    "Registered Provider of Social Housing",
    "Government Organisation",
    "Local Authority",
    "Universities",
]

PRIORITIES = [
    "GB-CHC",
    "GB-SC",
    "GB-NIC",
    "GB-COH",
    "GB-EDU",
    "GB-LAE",
    "GB-PLA",
    "GB-GOR"
]