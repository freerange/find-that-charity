import datetime
import re
import hashlib

from dateutil import parser

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
}

class Org():

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
        "sources",
        "telephone",
        "url",
        "streetAddress",
        "addressLocality",
        "addressRegion",
        "addressCountry",
    ]

    date_fields = [
        "dateRegistered",
        "dateRemoved",
        "dateModified"
    ]

    def __init__(self, id, source):
        self.id = id
        for f in self.fields:
            setattr(self, f, source.get(f))
        self._sort_out_date()


    def _sort_out_date(self):
        """
        parse date fields in a organisation record
        """
        for date_field in self.date_fields:
            if getattr(self, date_field):
                if isinstance(getattr(self, date_field), (datetime.date, datetime.datetime)):
                    continue
                try:
                    setattr(
                        self,
                        date_field,
                        parser.parse(
                            getattr(self, date_field)
                        )
                    )
                except ValueError:
                    pass

    def as_charity(self):
        charity_sources = set(["ccew", "oscr", "ccni"])
        if not charity_sources.intersection(self.sources):
            return None
            
        data = {
            "active": getattr(self, "active"),
            "known_as": getattr(self, "name"),
            "names": [
                {
                    "name": getattr(self, "name"),
                    "type": "Registered name",
                    "source": "+".join(self.sources),
                }
            ] + [
                {
                    "name": n,
                    "type": None,
                    "source": "+".join(self.sources),
                }
                for n in getattr(self, "alternateName", [])
            ],
            "geo": {
                "areas": [],
                "postcode": getattr(self, "postalCode"),
                "location": None,
            },
            "url": getattr(self, "url"),
            "domain": getattr(self, "domain"),
            "latest_income": getattr(self, "latestIncome"),
            "parent": getattr(self, "parent"),
            "company_number": getattr(self, "companyNumber"),
            "ccew_number": None,
            "oscr_number": None,
            "ccni_number": None,
            "ccew_link": None,
            "oscr_link": None,
            "ccni_link": None,
            "date_registered": getattr(self, "dateRegistered"),
            "date_removed": getattr(self, "dateRemoved"),
            "org-ids": getattr(self, "orgIDs"),
            "alt_names": getattr(self, "alternateName"),
            # "complete_names": getattr(self, ""),
            "last_modified": getattr(self, "dateModified"),
        }

        links = self.get_links(self.orgIDs)
        for link, linkname in links:
            if linkname=="Charity Commission England and Wales":
                data["ccew_link"] = link
            elif linkname=="Office of Scottish Charity Regulator":
                data["oscr_link"] = link
            elif linkname=="Charity Commission Northern Ireland":
                data["ccni_link"] = link

        for o in getattr(self, "orgIDs", []):
            for source, orgschema in [
                ("ccew", "GB-CHC"),
                ("oscr", "GB-SC"),
                ("ccni", "GB-NIC"),
            ]:
                if o.startswith(orgschema + "-"):
                    data[source + "_number"] = self.clean_regno(o.replace(orgschema + "-", ""), False)
        
        return data

    @staticmethod
    def clean_regno(regno, to_orgid=True):
        """
        Clean up a charity registration number
        """
        if regno.startswith("GB-"):
            return regno

        regno = str(regno)
        regno = regno.upper()
        regno = re.sub(r'^[^0-9SCNI]+|[^0-9]+$', '', regno)

        if regno.startswith("S"):
            orgid_scheme = 'GB-SC'
        elif regno.startswith("N"):
            orgid_scheme = 'GB-NIC'
            regno = re.sub(r'^[^0-9]+|[^0-9]+$', '', regno)
        else:
            orgid_scheme = 'GB-CHC'

        if to_orgid:
            return "{}-{}".format(orgid_scheme, regno)
        return regno
        
    @staticmethod
    def get_links(orgids):

        links = []
        for o in orgids:
            for prefix, ls in EXTERNAL_LINKS.items():
                if o.startswith(prefix + "-"):
                    regno = o.replace(prefix + "-", "")
                    for l in ls:
                        links.append((l[0].format(regno), l[1]))

        return links

class MergedOrg():

    fields = [
        "name", "charityNumber", "companyNumber",
        "telephone", "email", "description", 
        "url", "latestIncome", "dateModified",
        "dateRegistered", "dateRemoved",
        "active", "parent", "organisationType", 
        "alternateName", "orgIDs", "id"
    ]

    address_fields = [
        "streetAddress",
        "addressLocality",
        "addressRegion",
        "addressCountry",
        "postalCode",
    ]

    source_priority = [
        "ccew",
        "oscr",
        "ccni",
        "companies",
        "gias",
    ]
    
    charity_sources = set(["ccew", "oscr", "ccni"])

    def __init__(self, orgs):
        self.data = {}

        # get all the unique sources in the data
        sources = set()
        for org in orgs:
            sources.update(org.sources)

        # add the sources in the right priority order
        self.sources = [
            s for s in self.source_priority if s in list(sources)
        ] + [
            s for s in list(sources) if s not in self.source_priority
        ]

        # sort the organisations
        self.orgs = sorted(orgs, key=lambda o: self.sources.index(o.sources[0]))

        # go through each possible field
        for f in self.fields:
            self.data[f] = {}

            # go through each organisation in our data
            for org in self.orgs:

                # if there's nothing for this field in this org then move to the next one
                if not getattr(org, f):
                    continue

                # make sure the values are a list
                if isinstance(getattr(org, f), list):
                    value = getattr(org, f)
                    is_list = True
                else:
                    value = [getattr(org, f)]
                    is_list = False

                # go thorugh each of the values for this field
                for v in value:

                    value_key = hashlib.sha256(str(v).encode('utf-8')).hexdigest()[0:8]

                    # if we haven't seen this value before then add it
                    if value_key not in self.data[f]:
                        self.data[f][value_key] = {
                            "value": v,
                            "sources": [],
                            "is_list": is_list,
                        }

                    # record that we've used this source
                    self.data[f][value_key]["sources"].extend(org.sources)

        # look for address fields
        self.data["address"] = {}
        for org in self.orgs:

            address = {
                f: getattr(org, f) for f in self.address_fields if getattr(org, f, None)
            }
            value_key = hashlib.sha256("".join(address.values()).encode('utf-8')).hexdigest()[0:8]

            # if we haven't seen this value before then add it
            if value_key not in self.data["address"]:
                self.data["address"][value_key] = {
                    "value": address,
                    "sources": [],
                    "is_list": False,
                }

            # record that we've used this source
            self.data["address"][value_key]["sources"].extend(org.sources)

        self.name, self.names = self.get_names()
        self.id = self.get_main_value("id")
        self.active = self.get_main_value("active")
        self.links = Org.get_links(self.data["orgIDs"].keys())
    
    def get_names(self):
        main_name = self.get_main_value("name")
        names = {}
        for f in ["name", "alternateName"]:
            for k, v in self.data[f].items():
                if v["value"] == main_name:
                    continue
                if k in names:
                    names[k]["sources"].extend(v["sources"])
                    names[k]["sources"] = list(set(names[k]["sources"]))
                else:
                    names[k] = v
        return main_name, names

    def get_values(self, key):
        return [v.get("value") for v in list(self.data.get(key, {}).values())]

    def get_main_value(self, key, default=None):
        if not self.data.get(key, {}):
            return default
        
        vals = list(self.data.get(key, {}).values())
        if vals[0]["is_list"]:
            return [v["value"] for v in vals]
        else:
            return vals[0]["value"]

    def to_json(self):
        r_json = {
            "sources": self.sources,
            # "data": self.data,
        }

        for f in self.data.keys():
            r_json[f] = self.get_main_value(f)

        return r_json

    def as_charity(self):
        charity_sources = set(["ccew", "oscr", "ccni"])
        if not charity_sources.intersection(self.sources):
            return None
            
        data = {
            "active": self.get_main_value("active"),
            "known_as": self.get_main_value("name"),
            "names": [
                {
                    "name": n["value"],
                    "type": None,
                    "source": "+".join(n["sources"]),
                }
                for n in self.data.get("name", []).values()
            ] + [
                {
                    "name": n["value"],
                    "type": None,
                    "source": "+".join(n["sources"]),
                }
                for n in self.data.get("alternateName", []).values()
            ],
            "geo": {
                "areas": [],
                "postcode": self.get_main_value("address", {}).get("postalCode"),
                "location": None,
            },
            "url": self.get_main_value("url"),
            "domain": self.get_main_value("domain"),
            "latest_income": self.get_main_value("latestIncome"),
            "parent": self.get_main_value("parent"),
            "company_number": self.get_main_value("companyNumber"),
            "ccew_number": None,
            "oscr_number": None,
            "ccni_number": None,
            "ccew_link": None,
            "oscr_link": None,
            "ccni_link": None,
            "date_registered": self.get_main_value("dateRegistered"),
            "date_removed": self.get_main_value("dateRemoved"),
            "org-ids": self.get_main_value("orgIDs"),
            "alt_names": self.get_main_value("alternateName"),
            # "complete_names": getattr(self, ""),
            "last_modified": self.get_main_value("dateModified"),
        }

        links = Org.get_links(self.get_values("orgIDs"))
        for link, linkname in links:
            if linkname=="Charity Commission England and Wales":
                data["ccew_link"] = link
            elif linkname=="Office of Scottish Charity Regulator":
                data["oscr_link"] = link
            elif linkname=="Charity Commission Northern Ireland":
                data["ccni_link"] = link

        for o in self.get_values("orgIDs"):
            for source, orgschema in [
                ("ccew", "GB-CHC"),
                ("oscr", "GB-SC"),
                ("ccni", "GB-NIC"),
            ]:
                if o.startswith(orgschema + "-"):
                    data[source + "_number"] = Org.clean_regno(o.replace(orgschema + "-", ""), False)
        
        return data