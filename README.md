# Abu Dhabi Visa Decision Checker

A Streamlit app that lets applicants instantly check the status of their Irish visa application processed by the **Abu Dhabi Embassy**.

Data is sourced live from [ireland.ie](https://www.ireland.ie/en/uae/abudhabi/services/visas/weekly-decision-reports/) and refreshes every hour.

---

## Features

- Auto-fetches the latest weekly PDF decision report from the Irish Embassy Abu Dhabi
- Search by application number in any format: `63690452`, `IRL63690452`, or `irl63690452`
- Colour-coded results — green for approved, red for refused
- Shows nearest processed application numbers if yours isn't found yet
- Full dataset available as a CSV download

## How to Use

1. Enter your 8-digit application number (with or without the `IRL` prefix)
2. Click **Search**
3. If your number isn't found, the app shows the nearest processed numbers above and below yours

## Run Locally

```bash
git clone https://github.com/shayshankr/abudhabi.git
cd abudhabi
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Requirements

- Python 3.10+
- See `requirements.txt` for all dependencies

## File Structure

```
├── streamlit_app.py   # Streamlit app — scraping, PDF parsing, search UI
└── requirements.txt   # Python dependencies
```

## Data Source

Weekly visa decision reports are published by the Irish Embassy, Abu Dhabi:
[https://www.ireland.ie/en/uae/abudhabi/services/visas/weekly-decision-reports/](https://www.ireland.ie/en/uae/abudhabi/services/visas/weekly-decision-reports/)

Reports are published weekly in PDF format and cover decisions made during that week.

---

*Built to help the Irish visa community in the UAE.*
