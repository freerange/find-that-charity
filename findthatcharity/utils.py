import re
from dateutil import parser

def clean_regno(regno):
    """
    Clean up a charity registration number
    """
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
