import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

URL = "https://www.ireland.ie/en/uae/abudhabi/services/visas/weekly-decision-reports/"

def get_latest_report():
    response = requests.get(URL)
    if response.status_code != 200:
        return None, "Failed to fetch the webpage"

    soup = BeautifulSoup(response.text, "html.parser")

    # Find all links
    links = soup.find_all("a", href=True)

    # Regex pattern to match report titles
    pattern = re.compile(r"Abu Dhabi Visa Decision (\d{1,2} \w+ \d{4}) to (\d{1,2} \w+ \d{4})", re.IGNORECASE)

    latest_date = None
    latest_link = None
    latest_report_name = None

    for link in links:
        match = pattern.search(link.text)
        if match:
            report_date = match.group(2)  # Extract the end date
            if latest_date is None or report_date > latest_date:
                latest_date = report_date
                latest_report_name = link.text.strip()
                latest_link = link['href']

    if latest_link:
        return latest_report_name, latest_link
    else:
        return None, "No reports found"

# Streamlit UI
st.title("🇦🇪 Abu Dhabi Visa Decision Reports")
st.write("Fetching the latest visa decision report dynamically.")

latest_report, report_url = get_latest_report()

if latest_report:
    st.success(f"**Latest Report:** {latest_report}")
    st.markdown(f"[📥 Download Report]({report_url})", unsafe_allow_html=True)
else:
    st.error(report_url)
