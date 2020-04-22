import re
import typing
from datetime import date, datetime
import json
import unicodedata
from math import ceil

from dateutil import parser
from starlette.responses import JSONResponse

from .settings import DEFAULT_PAGE, DEFAULT_SIZE


def clean_regno(regno):
    """
    Clean up a charity registration number
    """
    if regno.startswith("GB-"):
        return regno

    regno = str(regno)
    regno = regno.upper()
    regno = re.sub(r'^[^0-9SCNI]+|[^0-9]+$', '', regno)

    if regno.startswith("S"):
        return "GB-SC-{}".format(regno)
    if regno.startswith("N"):
        return "GB-NIC-{}".format(re.sub(r'^[^0-9]+|[^0-9]+$', '', regno))
    return "GB-CHC-{}".format(regno)

def sort_out_date(record, date_fields=["dateRegistered", "dateRemoved", "dateModified"]):
    """
    parse date fields in a organisation record
    """
    for date_field in date_fields:
        if record.get(date_field):
            try:
                record[date_field] = parser.parse(
                    record[date_field])
            except ValueError:
                pass
    return record
    

def sort_out_orgtypes(orgtypes):
    return {
        slugify(o["key"]): {
            "key": o["key"],
            "doc_count": o["doc_count"],
            "slug": slugify(o["key"]),
        } for o in orgtypes
    }


def list_to_string(l):
    if not isinstance(l, list):
        return l
    
    if len(l)==1:
        return l[0]
    elif len(l)==2:
        return " and ".join(l)
    else:
        return ", ".join(l[0:-1]) + " and " + l[-1]

def get_links(orgids):
    links = []

    external_links = {
        "GB-CHC": [
            ["http://apps.charitycommission.gov.uk/Showcharity/RegisterOfCharities/SearchResultHandler.aspx?RegisteredCharityNumber={}&SubsidiaryNumber=0&Ref=CO", "Charity Commission England and Wales"],
            ["http://beta.charitycommission.gov.uk/charity-details/?regid={}&subid=0", "Charity Commission England and Wales (beta)"],
            ["https://charitybase.uk/charities/{}", "CharityBase"],
            ["http://opencharities.org/charities/{}", "OpenCharities"],
            ["http://www.guidestar.org.uk/summary.aspx?CCReg={}", "GuideStar"],
            ["http://www.charitychoice.co.uk/charities/search?t=qsearch&q={}", "Charities Direct"],
            ["https://olib.uk/charity/html/{}", "CharityData by Olly Benson"],
        ],
        "GB-NIC": [
            ["http://www.charitycommissionni.org.uk/charity-details/?regid={}&subid=0", "Charity Commission Northern Ireland"],
        ],
        "GB-SC": [
            ["https://www.oscr.org.uk/about-charities/search-the-register/charity-details?number={}", "Office of the Scottish Charity Register"],
        ],
        "GB-EDU": [
            ["https://get-information-schools.service.gov.uk/Establishments/Establishment/Details/{}", "Get information about schools"],
        ],
        "GB-NHS": [
            ["https://odsportal.hscic.gov.uk/Organisation/Details/{}", "NHS Digital"],
        ],
    }

    for o in orgids:
        for prefix, ls in external_links.items():
            if o.startswith(prefix + "-"):
                regno = o.replace(prefix + "-", "")
                for l in ls:
                    links.append((l[0].format(regno), l[1]))

    return links


class JSONResponseDate(JSONResponse):
    def render(self, content: typing.Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            default=self.json_serial
        ).encode("utf-8")

    @staticmethod
    def json_serial(obj):
        """JSON serializer for objects not serializable by default json code"""

        if isinstance(obj, (datetime, date)):
            return obj.isoformat()

        from .classes.org import MergedOrg, Org
        if isinstance(obj, (MergedOrg, Org)):
            return obj.to_json()

        raise TypeError ("Type %s not serializable" % type(obj))

def slugify(string):

    """
    Slugify a unicode string.

    Example:

        >>> slugify(u"Héllø Wörld")
        u"hello-world"

    """
    string = unicodedata.normalize('NFKD', string)
    string = re.sub(r'[^\w\s-]', '', string).strip().lower()
    string = re.sub(r'[-\s]+', '-', string)
    return string

def pagination(p, size, total):
    pages = {
        'current_page': p,
        'size': size,
        'total_items': total,
        'total_pages': ceil(total / size),
    }
    if p > 1:
        pages['previous_page'] = p - 1
    if p > 2:
        pages['first_page'] = 1
    if pages['total_pages'] > p:
        pages['next_page'] = p + 1
    if pages['total_pages'] > (p+1):
        pages['last_page'] = pages['total_pages']
    pages['start_item'] = ((p-1) * size) + 1
    pages['end_item'] = min([total, p*size])
    return pages

def pagination_request(request, defaultsize=DEFAULT_SIZE, defaultpage=DEFAULT_PAGE, maxsize=100):

    try:
        page = int(request.query_params.get("p", defaultpage))
        if page < 1:
            raise ValueError()
    except ValueError:
        page = defaultpage

    try:
        size = int(request.query_params.get("size", defaultsize))
        if size > maxsize:
            raise ValueError()
    except ValueError:
        size = defaultsize

    return {
        "p": page, "size": size, "from": (page-1) * size
    }
