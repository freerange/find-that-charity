import re
from dateutil import parser

def clean_regno(regno):
    """
    Clean up a charity registration number
    """
    regno = str(regno)
    regno = regno.upper()
    regno = re.sub(r'^[^0-9SCNI]+|[^0-9]+$', '', regno)
    return regno

def sort_out_date(charity_record):
    """
    parse date fields in a charity record
    """
    date_fields = ["date_registered", "date_removed", "last_modified"]
    for date_field in date_fields:
        if charity_record.get(date_field):
            try:
                charity_record[date_field] = parser.parse(
                    charity_record[date_field])
            except ValueError:
                pass
    return charity_record