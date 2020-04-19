import json

from starlette.routing import Route
from starlette.responses import Response
from sqlalchemy import select

from ..db import db_con, scrape
from ..utils import JSONResponseDate

async def get_scrapes(request):
    scrapes = db_con.execute(
            select(scrape.columns)
        ).fetchall()
    return JSONResponseDate({
        "scrapes": [
            {
                **s,
                "stats": json.loads(s['stats'])
            } for s in scrapes
        
        ]
    })

routes = [
    Route('/scrapes', get_scrapes),
]
