import pandas as pd
import os
import re
import pandas as pd
from pypdf import PdfReader
from geotext import GeoText

# load data
phmsa = pd.read_csv(r"phmsa_enforcement_accident\PHMSA_Raw_Data.csv")

#define criteria for Corrective_Action_Order_Ind = YES
CAO = phmsa[phmsa["Corrective_Action_Order_Ind"] == "Yes"]

# extract the text before first hyphen
CAO["Material"] = CAO["Report_Number"].str.split("-").str[0].str.strip()

# count frequencies
material_counts = CAO["Material"].value_counts()

print(material_counts)

print(CAO.shape)

print(85+54+1)

incident_reports = phmsa[phmsa["Report_Type"] == "Incident Report"]

print(incident_reports)



US_STATES = [
    "Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut","Delaware",
    "Florida","Georgia","Hawaii","Idaho","Illinois","Indiana","Iowa","Kansas","Kentucky",
    "Louisiana","Maine","Maryland","Massachusetts","Michigan","Minnesota","Mississippi",
    "Missouri","Montana","Nebraska","Nevada","New Hampshire","New Jersey","New Mexico",
    "New York","North Carolina","North Dakota","Ohio","Oklahoma","Oregon","Pennsylvania",
    "Rhode Island","South Carolina","South Dakota","Tennessee","Texas","Utah","Vermont",
    "Virginia","Washington","West Virginia","Wisconsin","Wyoming"
]

def extract_location_from_pdf(pdf_path):
    # read first page text
    reader = PdfReader(pdf_path)
    try:
        text = reader.pages[0].extract_text() or ""
    except Exception:
        text = ""
    text = " ".join(text.split())  # normalize whitespace

    # find "inspected" (word boundary, case-insensitive)
    m = re.search(r"\binspected\b", text, flags=re.IGNORECASE)
    if not m:
        return None, None, None

    # start AFTER the word "inspected"
    start = m.end()

    # take up to the first period after "inspected"
    period_idx = text.find(".", start)
    if period_idx == -1:
        snippet = text[start:].strip()
    else:
        snippet = text[start:period_idx].strip()

    # remove leading punctuation/comma/colon and common prepositions like "at", "in"
    snippet = re.sub(r'^[\s,;:-]+', '', snippet)
    snippet = re.sub(r'^(?:at|in|on|near|inside|outside)\b[\s,:-]*', '', snippet, flags=re.IGNORECASE)
    raw_snippet = snippet  # keep for debug / inspection

    # get city via GeoText
    places = GeoText(snippet)
    city = places.cities[0] if places.cities else None

    # match full-state names from US_STATES (case-insensitive, escaped)
    matched_states = []
    for st in US_STATES:
        pattern = rf"\b{re.escape(st)}\b"
        if re.search(pattern, snippet, flags=re.IGNORECASE):
            matched_states.append(st)

    # If multiple states matched, join them; otherwise None
    state = ", ".join(matched_states) if matched_states else None

    return city, state, raw_snippet


def process_pdfs_in_folder(folder_path):
    rows = []
    for fname in os.listdir(folder_path):
        if not fname.lower().endswith(".pdf"):
            continue
        path = os.path.join(folder_path, fname)
        city, state, raw_snippet = extract_location_from_pdf(path)
        rows.append({
            "pdf_name": fname,
            "city": city,
            "state": state,
            "raw_snippet": raw_snippet
        })
    return pd.DataFrame(rows)


# apply to folder
folder = r"phmsa_enforcement_accident\pdf"
df = process_pdfs_in_folder(folder)
print(df)
# optional: df.to_csv("inspected_locations.csv", index=False)


