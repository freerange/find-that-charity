from starlette.config import Config
from starlette.datastructures import URL, Secret

config = Config(".env")

DEBUG = config('DEBUG', cast=bool, default=False)
TESTING = config('TESTING', cast=bool, default=False)
SECRET_KEY = config('SECRET_KEY', cast=Secret)

ES_URL = config('ES_URL', cast=URL)
if TESTING:
    ES_URL = ES_URL.replace(database='test_' + ES_URL.database)
ES_INDEX = config('ES_INDEX', default='charitysearch')
ES_TYPE = config('ES_TYPE', default='charity')
