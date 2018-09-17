"""
Script for fetching data from charity regulators
"""
import urllib.request
import urllib.parse
import argparse
import re
import os

from bs4 import BeautifulSoup

EDU_URL = "https://get-information-schools.service.gov.uk/Downloads"
SCOT_URL = "https://www.gov.scot/Topics/Statistics/Browse/School-Education/Datasets/contactdetails"
NI_URL = "http://apps.education-ni.gov.uk/appinstitutes/default.aspx"

def main():
    """
    Function to fetch data from Education regulators
    """
    parser = argparse.ArgumentParser(description='Fetch needed education data sources.')
    parser.add_argument('--gias', type=str,
                        default=EDU_URL,
                        help="URL of download page for schools in England")
    parser.add_argument('--skip-gias', action='store_true',
                        help='Don\'t fetch data from Get Information About Schools in England.')
    parser.add_argument('--scot', type=str,
                        default=SCOT_URL,
                        help="URL of download page for schools in Scotland")
    parser.add_argument('--skip-scot', action='store_true',
                        help='Don\'t fetch data from about Schools in Scotland.')
    parser.add_argument('--ni', type=str,
                        default=NI_URL,
                        help="URL of download page for schools in Northern Ireland")
    parser.add_argument('--skip-ni', action='store_true',
                        help='Don\'t fetch data from about Schools in Northern Ireland.')
    parser.add_argument('--folder', type=str, default='data',
                        help='Root path of the data folder.')
    args = parser.parse_args()

    # make folder if it's not already there
    if not os.path.exists(args.folder):
        os.makedirs(args.folder)

    # Fetch schools in England
    if not args.skip_gias:
        gias_out = os.path.join(args.folder, "gias_england.csv")
        gias_html = urllib.request.urlopen(args.gias)
        gias_soup = BeautifulSoup(gias_html.read(), 'html.parser')
        gias_regex = re.compile(r"http://ea-edubase-api-prod.azurewebsites.net/edubase/edubasealldata[0-9]{8}\.csv")
        gias_data_url = gias_soup.find("a", href=gias_regex)["href"]
        print("[GIAS] Using url: %s" % gias_data_url)
        urllib.request.urlretrieve(gias_data_url, gias_out)
        print("[GIAS] CSV downloaded")

    # Fetch schools in Scotland
    if not args.skip_scot:
        scot_out = os.path.join(args.folder, "schools_scotland.xlsx")
        scot_html = urllib.request.urlopen(args.scot)
        scot_soup = BeautifulSoup(scot_html.read(), 'html.parser')
        scot_regex = re.compile(r".*\.xlsx")
        scot_data_url = urllib.parse.urljoin(
            args.scot,
            scot_soup.find("a", href=scot_regex)["href"]
        )
        print("[SCOTLAND] Using url: %s" % scot_data_url)
        urllib.request.urlretrieve(scot_data_url, scot_out)
        print("[SCOTLAND] XLSX downloaded")

    # Fetch schools in Northern Ireland
    if not args.skip_ni:
        ni_out = os.path.join(args.folder, "schools_ni.csv")
        ni_html = urllib.request.urlopen(args.ni)
        ni_soup = BeautifulSoup(ni_html.read(), 'html.parser')
        post_params = {
            "__EVENTARGUMENT": "",
            "__EVENTTARGET": "",
            "__EVENTVALIDATION": "",
            "__VIEWSTATE": "",
            "__VIEWSTATEENCRYPTED": "",
            "__VIEWSTATEGENERATOR": "",
            "as_fid": "",
            "as_sfid": "",
            "ctl00$ContentPlaceHolder1$instAddr$instAddr_hfv": "",
            "ctl00$ContentPlaceHolder1$instCounty": "",
            "ctl00$ContentPlaceHolder1$instMgt": "",
            "ctl00$ContentPlaceHolder1$instName$instName_hfv": "",
            "ctl00$ContentPlaceHolder1$instPhone$instPhone_hfv": "",
            "ctl00$ContentPlaceHolder1$instPostcode$instPostcode_hfv": "",
            "ctl00$ContentPlaceHolder1$instRef$instRef_hfv": "",
            "ctl00$ContentPlaceHolder1$instStatus": "-1",
            "ctl00$ContentPlaceHolder1$instTown": "",
            "ctl00$ContentPlaceHolder1$instType": "-1",
            "ctl00$ContentPlaceHolder1$lvSchools$exportFilename$exportFilename_hfv": "U2Nob29sc19QbHVzXzE3X1NlcF8yMDE4XzExXzQ3",
            "ctl00$ContentPlaceHolder1$lvSchools$exportType": "2",
        }
        for p in post_params:
            try:
                post_params[p] = ni_soup.find('input', {'name': p}).get('value', "")
            except:
                pass
        post_params["ctl00$ContentPlaceHolder1$lvSchools$exportType"] = "2"
        post_params["__EVENTTARGET"] = "ctl00$ContentPlaceHolder1$lvSchools$btnDoExport"
        print(post_params)

        print("[NI] Using url: %s" % args.ni)
        urllib.request.urlretrieve(
            args.ni, ni_out, data=urllib.parse.urlencode(post_params).encode("utf-8"))
        print("[NI] CSV downloaded")


if __name__ == '__main__':
    main()
