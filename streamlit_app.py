import streamlit as st
import pandas as pd
import bisect
from io import BytesIO
import requests
from bs4 import BeautifulSoup
import re

URL = "https://www.ireland.ie/en/uae/abudhabi/services/visas/weekly-decision-reports/"

def get_latest_report():
    response = requests.get(URL)
    if response.status_code != 200:
        print("Failed to fetch the webpage")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # Find all links
    links = soup.find_all("a", href=True)

    # Regex pattern to match report titles
    pattern = re.compile(r"Abu Dhabi Visa Decision (\d{1,2} \w+ \d{4}) to (\d{1,2} \w+ \d{4})", re.IGNORECASE)

    latest_date = None
    latest_link = None

    for link in links:
        match = pattern.search(link.text)
        if match:
            report_date = match.group(2)  # Extract the end date
            if latest_date is None or report_date > latest_date:
                latest_date = report_date
                latest_link = link['href']

    if latest_link:
        print(f"Latest report URL: {latest_link}")
        return latest_link
    else:
        print("No reports found.")
        return None

latest_report_url = get_latest_report()

