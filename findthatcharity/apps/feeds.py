from datetime import datetime, timezone

from dateutil import parser
from starlette.applications import Starlette
from starlette.responses import JSONResponse
import requests
from bs4 import BeautifulSoup

from ..templates import templates

CCEW_URL = 'http://data.charitycommission.gov.uk/'

app = Starlette()

@app.route('/ccew.{filetype}')
async def ccew_rss(request):
    """
    Get an RSS feed based on when data is
    uploaded by the Charity Commission
    """
    res = requests.get(CCEW_URL)
    soup = BeautifulSoup(res.text, 'html.parser')
    items = []
    for i in soup.find_all('blockquote'):
        links = i.find_all('a')
        idate = parser.parse(
            i.h4.string.split(", ")[1],
            default=datetime(2018, 1, 12, 0, 0)
        ).replace(tzinfo=timezone.utc)
        items.append({
            "name": i.h4.string,
            "date": idate,
            "link": links[0].get('href'),
            "author": "Charity Commission for England and Wales",
        })

    feed_contents = dict(
        items=items,
        title='Charity Commission for England and Wales data downloads',
        description='Downloads available from Charity Commission data downloads page.',
        url=CCEW_URL,
        feed_url=str(request.url),
        updated=datetime.now().replace(tzinfo=timezone.utc),
        request=request,
    )

    if request.path_params['filetype'] == 'atom':
        content_type = 'application/atom+xml'
        template = 'atom.xml'
    elif request.path_params['filetype'] == "json":
        return JSONResponse({
            "version": "https://jsonfeed.org/version/1",
            "title": feed_contents["title"],
            "home_page_url": feed_contents["url"],
            "feed_url": feed_contents["feed_url"],
            "description": feed_contents["description"],
            "items": [
                {
                    "id": item["link"],
                    "url": item["link"],
                    "title": item["name"],
                    "date_published": item["date"].isoformat(),
                } for item in items
            ]
        }, media_type='application/json')
    else:
        content_type = 'application/rss+xml'
        template = 'rss.xml'

    return templates.TemplateResponse(template, feed_contents, media_type=content_type)