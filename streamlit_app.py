import re
import requests
import pandas as pd
import streamlit as st
from io import BytesIO
from datetime import datetime
from bs4 import BeautifulSoup

BASE_URL = "https://www.ireland.ie/en/uae/abudhabi/services/visas/weekly-decision-reports/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    )
}

# Matches: "Abu Dhabi Visa decisions 26th Apr to 1st May"
LINK_PATTERN = re.compile(
    r"Abu Dhabi Visa decisions\s+(\d{1,2}(?:st|nd|rd|th)?\s+\w+)\s+to\s+(\d{1,2}(?:st|nd|rd|th)?\s+\w+)",
    re.IGNORECASE,
)


def _parse_ordinal_date(date_str: str, reference_year: int = None) -> datetime:
    """Parse dates like '26th Apr', '1st May', '19th Apr' into datetime."""
    # Strip ordinal suffix
    cleaned = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", date_str).strip()
    if reference_year:
        cleaned = f"{cleaned} {reference_year}"
        for fmt in ("%d %B %Y", "%d %b %Y"):
            try:
                return datetime.strptime(cleaned, fmt)
            except ValueError:
                continue
    # Try without year — use current year
    year = datetime.now().year
    for fmt in ("%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(f"{cleaned} {year}", fmt)
        except ValueError:
            continue
    return datetime.min


@st.cache_data(ttl=3600)
def get_latest_report() -> tuple:
    """Scrape the page and return (report_name, absolute_url, error)."""
    try:
        response = requests.get(BASE_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        return None, None, str(e)

    soup = BeautifulSoup(response.text, "html.parser")
    latest_date = datetime.min
    latest_link = None
    latest_name = None

    for link in soup.find_all("a", href=True):
        text = link.text.strip()
        match = LINK_PATTERN.search(text)
        if match:
            end_date = _parse_ordinal_date(match.group(2))
            if end_date > latest_date:
                latest_date = end_date
                latest_name = text
                href = link["href"]
                latest_link = href if href.startswith("http") else requests.compat.urljoin(BASE_URL, href)

    if latest_link:
        return latest_name, latest_link, None
    return None, None, "No reports found on the page."


@st.cache_data(ttl=3600)
def download_and_parse_pdf(report_url: str) -> tuple:
    """Download the PDF and extract application numbers + decisions. Returns (df, error)."""
    try:
        r = requests.get(report_url, headers=HEADERS, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        return None, str(e)

    try:
        import pypdf
        reader = pypdf.PdfReader(BytesIO(r.content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except ImportError:
        return None, "pypdf not installed — cannot parse PDF content."
    except Exception as e:
        return None, f"PDF parsing failed: {e}"

    # Extract rows: application number followed by decision on the same line
    # Common pattern in Irish Embassy PDFs: number<whitespace>decision
    app_pattern = re.compile(
        r"(IRL\d{8}|\d{8})\s+(Approved|Refused|Granted|Rejected|Pending|Withdrawn)",
        re.IGNORECASE,
    )
    rows = []
    for match in app_pattern.finditer(text):
        rows.append({
            "Application Number": match.group(1).strip().upper(),
            "Decision": match.group(2).strip().capitalize(),
        })

    if not rows:
        return None, "Could not extract application records from the PDF."

    df = pd.DataFrame(rows).drop_duplicates(subset="Application Number").reset_index(drop=True)
    return df, None


def normalize(value: str) -> str:
    return value.strip().upper().removeprefix("IRL")


def validate_input(raw: str) -> tuple:
    raw = raw.strip()
    if not raw:
        return False, "", ""
    if not re.match(r"^[A-Za-z0-9]+$", raw):
        return False, "No spaces or special characters allowed. Use `IRL12345678` or `12345678`", ""
    upper = raw.upper()
    numeric_part = raw[3:] if upper.startswith("IRL") else raw
    if upper.startswith("IRL") and not numeric_part.isdigit():
        return False, "After `IRL` only digits are allowed. Example: `IRL63690452`", ""
    if not upper.startswith("IRL") and not raw.isdigit():
        return False, "Only the prefix `IRL` is allowed. Use `IRL12345678` or `12345678`", ""
    if len(numeric_part) != 8:
        return False, f"Must be exactly 8 digits (got {len(numeric_part)}). Example: `IRL63690452`", ""
    return True, "", numeric_part


def search_application(application_number: str, df: pd.DataFrame):
    is_valid, error_msg, normalized = validate_input(application_number)
    if not is_valid:
        if error_msg:
            st.error(f"❌ {error_msg}")
        return

    df_norm = df["Application Number"].apply(normalize)
    result = df[df_norm == normalized]

    if not result.empty:
        decision = result.iloc[0]["Decision"]
        app_num = result.iloc[0]["Application Number"]
        d = decision.lower()
        if "approv" in d or "grant" in d:
            st.success(f"**Application {app_num} — Decision: {decision}** ✅")
        elif "refus" in d or "reject" in d:
            st.error(f"**Application {app_num} — Decision: {decision}** ❌")
        else:
            st.info(f"**Application {app_num} — Decision: {decision}**")
        return

    st.warning(f"No record found for Application Number: {normalized}.")

    try:
        query_int = int(normalized)
        nums = (
            df["Application Number"]
            .apply(lambda x: int(normalize(x)) if normalize(x).isdigit() else None)
            .dropna()
            .astype(int)
        )
        below = nums[nums < query_int]
        above = nums[nums > query_int]
        rows = []
        if not below.empty:
            n = below.max()
            row = df[nums == n].iloc[0]
            rows.append({"Position": "Before", "Application Number": str(row["Application Number"]),
                         "Decision": row["Decision"], "Difference": query_int - n})
        if not above.empty:
            n = above.min()
            row = df[nums == n].iloc[0]
            rows.append({"Position": "After", "Application Number": str(row["Application Number"]),
                         "Decision": row["Decision"], "Difference": n - query_int})
        if rows:
            st.subheader("Nearest Application Numbers")
            header = "| Position | Application Number | Decision | Difference |\n|---|---|---|---|"
            body = "\n".join(
                f"| {r['Position']} | {r['Application Number']} | {r['Decision']} | {r['Difference']} |"
                for r in rows
            )
            st.markdown(f"{header}\n{body}")
        else:
            st.info("No nearest application numbers found.")
    except ValueError:
        pass


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Abu Dhabi Visa Decision Checker",
    page_icon="🇦🇪",
    layout="centered",
)

st.title("🇦🇪 Abu Dhabi Visa Decision Checker")
st.caption("Irish Embassy Abu Dhabi · Data sourced from ireland.ie")

with st.expander("How to use this tool"):
    st.markdown("""
    1. The app auto-fetches the latest weekly PDF decision report from the Irish Embassy Abu Dhabi.
    2. Enter your 8-digit application number (e.g. `63690452` or `IRL63690452`).
    3. Click **Search** to see your decision instantly.
    4. If not found, the app shows the nearest processed numbers above and below yours.
    """)

# ── Fetch latest report link ──────────────────────────────────────────────────
with st.spinner("Fetching latest report from ireland.ie…"):
    report_name, report_url, fetch_error = get_latest_report()

if fetch_error:
    st.error(f"Could not load data: {fetch_error}")
    st.stop()

st.success(f"**{report_name}**")
st.markdown(f"[📥 Download PDF report]({report_url})")

# ── Parse PDF ─────────────────────────────────────────────────────────────────
with st.spinner("Parsing PDF report…"):
    df, parse_error = download_and_parse_pdf(report_url)

if parse_error:
    st.warning(f"Could not parse decision data from the PDF: {parse_error}")
    st.info("You can still download the PDF using the link above to check manually.")
    st.stop()

# ── Stats ─────────────────────────────────────────────────────────────────────
total = len(df)
decisions = df["Decision"].value_counts()
col1, col2, col3 = st.columns(3)
col1.metric("Total Decisions", total)
col2.metric("Approved", int(decisions.get("Approved", decisions.get("Granted", 0))))
col3.metric("Refused", int(decisions.get("Refused", decisions.get("Rejected", 0))))

st.divider()

# ── Search ────────────────────────────────────────────────────────────────────
st.subheader("Check your application")
st.caption("Valid formats: `63690452` · `IRL63690452` · `irl63690452` — exactly 8 digits, optional IRL prefix")

application_number = st.text_input(
    "Enter Application Number:",
    placeholder="e.g. IRL63690452 or 63690452",
    max_chars=11,
)

if st.button("Search"):
    if application_number:
        search_application(application_number, df)
    else:
        st.warning("Please enter an Application Number to search.")

st.divider()

# ── Download CSV ──────────────────────────────────────────────────────────────
csv = df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇️ Download dataset as CSV",
    data=csv,
    file_name="abudhabi_visa_decisions.csv",
    mime="text/csv",
)

st.caption(f"Data refreshes every hour. [Source]({BASE_URL})")
