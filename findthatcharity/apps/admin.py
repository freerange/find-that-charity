import json

from starlette.routing import Route
from starlette.responses import Response
from sqlalchemy import select, desc

from ..db import db_con, scrape
from ..utils import JSONResponseDate
from ..templates import templates

async def get_scrapes(request):
    scrapes = db_con.execute(
            select(scrape.columns, order_by=desc(scrape.c.start_time))
        )

    scrapes = [
        {
            **s,
            "stats": json.loads(s['stats']),
            "start_date": s["start_time"].date(),
        } for s in scrapes
    
    ]

    return templates.TemplateResponse('admin/scrapes.html', {
        'request': request,
        'scrapes': scrapes
    })
    return JSONResponseDate({
        "scrapes": scrapes
    })

async def get_scrape(request):
    scrape_ = db_con.execute(
            select(
                scrape.columns,
                order_by=desc(scrape.c.start_time),
                whereclause=(scrape.c.id==request.path_params.get('scrape_id'))
            )
        ).fetchone()

    scrape_ = {
        **scrape_,
        "stats": json.loads(scrape_['stats']),
    }

    return templates.TemplateResponse('admin/scrape.html', {
        'request': request,
        'scrape': scrape_
    })
    return JSONResponseDate({
        "scrape": scrape_
    })

routes = [
    Route('/scrapes', get_scrapes),
    Route('/scrape/{scrape_id}', get_scrape, name='get_scrape'),
]

