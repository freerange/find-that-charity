import datetime
import re
import hashlib

from dateutil import parser
from sqlalchemy import select, or_
from ..utils import slugify

from ..db import organisation, organisation_links

EXTERNAL_LINKS = {
    "GB-CHC": [
        ["http://apps.charitycommission.gov.uk/Showcharity/RegisterOfCharities/SearchResultHandler.aspx?RegisteredCharityNumber={}&SubsidiaryNumber=0&Ref=CO", "Charity Commission England and Wales"],
        ["http://beta.charitycommission.gov.uk/charity-details/?regid={}&subid=0", "Charity Commission England and Wales (beta)"],
        ["https://charitybase.uk/charities/{}", "CharityBase"],
        ["http://opencharities.org/charities/{}", "OpenCharities"],
        ["http://www.guidestar.org.uk/summary.aspx?CCReg={}", "GuideStar"],
        ["http://www.charitychoice.co.uk/charities/search?t=qsearch&q={}", "Charities Direct"],
        ["https://olib.uk/charity/html/{}", "CharityData by Olly Benson"],
    ],
    "GB-COH": [
        ["https://beta.companieshouse.gov.uk/company/{}", "Companies House"],
        ["https://opencorporates.com/companies/gb/{}", "Opencorporates"],
    ],
    "GB-NIC": [
        ["http://www.charitycommissionni.org.uk/charity-details/?regid={}&subid=0", "Charity Commission Northern Ireland"],
    ],
    "GB-SC": [
        ["https://www.oscr.org.uk/about-charities/search-the-register/charity-details?number={}", "Office of Scottish Charity Regulator"],
    ],
    "GB-EDU": [
        ["https://get-information-schools.service.gov.uk/Establishments/Establishment/Details/{}", "Get information about schools"],
    ],
    "GB-NHS": [
        ["https://odsportal.hscic.gov.uk/Organisation/Details/{}", "NHS Digital"],
    ],
    "GB-LAE": [
        ["https://www.registers.service.gov.uk/registers/local-authority-eng/records/{}", "Local authorities in England"],
    ],
    "GB-LAN": [
        ["https://www.registers.service.gov.uk/registers/local-authority-nir/records/{}", "Local authorities in Northern Ireland"],
    ],
    "GB-LAS": [
        ["https://www.registers.service.gov.uk/registers/local-authority-sct/records/{}", "Local authorities in Scotland"],
    ],
    "GB-PLA": [
        ["https://www.registers.service.gov.uk/registers/principal-local-authority/records/{}", "Principal Local authorities in Wales"],
    ],
    "GB-GOR": [
        ["https://www.registers.service.gov.uk/registers/government-organisation/records/{}", "Government organisations on GOV.UK"],
    ],
    "XI-GRID": [
        ["https://www.grid.ac/institutes/{}", "Global Research Identifier Database"],
    ],
}

class Org:

    fields = [
        "name",
        "orgIDs",
        "alternateName",
        "organisationType",
        "sources",
        "active",
        "postalCode",
    ]

    def __init__(self, id, **kwargs):
        self.id = id
        for f in self.fields:
            setattr(self, f, kwargs.get(f))
        self.organisationType = {slugify(t): t for t in self.organisationType}
        self.records = []

    def __repr__(self):
        return "<Org {}>".format(self.id)

    @classmethod
    def from_es(cls, id, es, es_index, es_type='_doc'):
        record = es.get(
            index=es_index,
            doc_type=es_type,
            id=id,
            _source_includes=cls.fields,
            ignore=[404]
        )
        return cls(record.get('_id'), **record.get("_source"))

    def _sort_records(self):
        self.records = [o for o in self.records if o.active] + \
            [o for o in self.records if not o.active]

    def fetch_records(self, db, table):
        records = db.execute(
            select(
                [table], 
                table.c.id.in_(self.orgIDs)
            )
        ).fetchall()
        self.records = [OrgRecord(**dict(r)) for r in records]
        self._sort_records()
        self.main = self.records[0]

    def fetch_org_links(self, db):
        org_links = db.execute(
            select(
                [organisation_links], 
                or_(
                    organisation_links.c.organisation_id_a.in_(self.orgIDs),
                    organisation_links.c.organisation_id_b.in_(self.orgIDs),
                )
            )
        ).fetchall()
        self.org_links = [dict(r) for r in org_links]
        self.sources = list(set(self.sources + [r['source'] for r in self.org_links]))

    def first(self, field):
        for r in self.records:
            if getattr(r, field, None):
                return {
                    "value": getattr(r, field),
                    "orgid": r.id,
                    "source": r.source,
                }

    def get_orgids(self):
        seen = set()
        for org in self.records:
            for id in org.orgIDs:
                if id not in seen:
                    yield {
                        "value": id,
                        "active": org.active,
                        "orgid": org.id,
                        "source": org.source,
                    }
                seen.add(id)


class OrgRecord:

    fields = [
        "name",
        "active",
        "alternateName",
        "charityNumber",
        "companyNumber",
        "dateModified",
        "dateRegistered",
        "dateRemoved",
        "description", 
        "domain", 
        "email",
        "latestIncome",
        "organisationType", 
        "orgIDs",
        "parent",
        "postalCode",
        "source",
        "telephone",
        "url",
        "streetAddress",
        "addressLocality",
        "addressRegion",
        "addressCountry",
        "location",
    ]

    date_fields = [
        "dateRegistered",
        "dateRemoved",
        "dateModified"
    ]

    def __init__(self, id, **kwargs):
        self.id = id
        for f in self.fields:
            setattr(self, f, kwargs.get(f))

    def __repr__(self):
        return "<OrgRecord {}>".format(self.id)

    @classmethod
    def from_db(cls, id, db, table):
        record = db.execute(
            select(
                [table], 
                table.c.id.in_(self.orgIDs)
            )
        ).fetchone()
        return cls(record['id'], **record)
                
    def get_links(self):
        for o in self.orgIDs:
            for prefix, ls in EXTERNAL_LINKS.items():
                if o.startswith(prefix + "-"):
                    regno = o.replace(prefix + "-", "")
                    for l in ls:
                        yield (l[0].format(regno), l[1])
