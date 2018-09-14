"""
Script for fetching data from charity regulators
"""
import urllib.request
import argparse
import zipfile
import re
import os

from bs4 import BeautifulSoup

EDU_URL = "https://get-information-schools.service.gov.uk/Downloads"

def main():
    """
    Function to fetch data from Education regulators
    """
    parser = argparse.ArgumentParser(description='Fetch needed education data sources.')
    parser.add_argument('--gias', type=str,
                        default=EDU_URL,
                        help="URL of download page for schools in England")
    parser.add_argument('--skip-gias', action='store_true',
                        help='Don\'t fetch data from Get Information About Schoools in England.')
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


if __name__ == '__main__':
    main()
