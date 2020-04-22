import json
from datetime import timezone

from starlette.routing import Route
from starlette.responses import Response
from sqlalchemy import select, desc
from feedgen.feed import FeedGenerator

from ..db import db_con, scrape
from ..utils import JSONResponseDate
from ..templates import templates

async def get_scrapes(request):
    scrapes = db_con.execute(
            select(
                scrape.columns,
                order_by=desc(scrape.c.start_time),
                limit=1000,
            )
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


async def get_scrapes_feed(request):
    where = None
    if "errorsonly" in request.query_params:
        where = (scrape.c.errors > 0)

    scrapes = db_con.execute(
            select(
                scrape.columns,
                order_by=desc(scrape.c.start_time),
                limit=50,
                whereclause=where,
            )
        )
    
    feedformat = 'atom' if request.query_params.get('format') == 'atom' else 'rss'

    fg = FeedGenerator()
    fg.id(request.url_for('get_scrapes_feed'))
    fg.title('Find that Charity scrapers')
    fg.author({'name':'Find that Charity'} )
    fg.link(href=request.url_for('get_scrapes'), rel='alternate' )
    # fg.logo('http://ex.com/logo.jpg')
    fg.subtitle('Results of find that charity scrapers')
    fg.link(href=request.url_for('get_scrapes_feed'), rel='self' )
    fg.language('en')

    for s in scrapes:
        stats = json.loads(s['stats'])
        fe = fg.add_entry()
        fe.id(request.url_for('get_scrape', scrape_id=s['id']))
        fe.published(s['start_time'].replace(tzinfo=timezone.utc))
        if s['finish_time']:
            fe.updated(s['finish_time'].replace(tzinfo=timezone.utc))
        else:
            fe.updated(s['start_time'].replace(tzinfo=timezone.utc))
        fe.summary(f'''
Spider {s['spider']} completed.

Took {stats.get("elapsed_time_seconds", 0):,.1f} seconds.

{s['items']:,.0f} items found.
        ''')
        if s['errors'] > 0:
            fe.title('Spider {} completed'.format(s['spider']))
        else:
            fe.title('Spider {} completed with errors'.format(s['spider']))
        fe.link(href=request.url_for('get_scrape', scrape_id=s['id']))

    if feedformat == 'atom':
        return Response(
            fg.atom_str(pretty=True),
            media_type='text/plain',
            # media_type='application/atom+xml',
        )
    return Response(
        fg.rss_str(pretty=True),
        media_type='text/plain',
        # media_type='application/rss+xml',
    )

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
    Route('/scrapes/feed', get_scrapes_feed),
    Route('/scrapes', get_scrapes),
    Route('/scrape/{scrape_id}', get_scrape, name='get_scrape'),
]

