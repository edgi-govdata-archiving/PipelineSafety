import pandas as pd
import os
import re
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from pypdf import PdfReader
from geotext import GeoText


# load data
phmsa = pd.read_csv(r"Data/PHMSA_Raw_Data.csv")

#define criteria for cases with Corrective_Action_Order
CAO = phmsa[phmsa["Corrective_Action_Order_Ind"] == "Yes"]

# extract the text before first hyphen
CAO["Material"] = CAO["Report_Number"].str.split("-").str[0].str.strip()

# count frequencies
material_counts = CAO["Material"].value_counts()

print(material_counts)

#define the criteria for cases with incident reports (and therefore location data)

incident_reports = phmsa[phmsa["Report_Type"] == "Incident Report"]

print(incident_reports)

#incident_reports.to_csv("incident_reports.csv")

#plot cases with incident reports by type over time 
# summarize penalty data by year and case type

penalties_ir = incident_reports[['Opened_Year','CPF_Number','Case_Type','Proposed_Penalties','Assessed_Penalties']].groupby(['Opened_Year','Case_Type']).sum()[['Proposed_Penalties','Assessed_Penalties']]
penalties_ir['num_cases'] = incident_reports.groupby(['Opened_Year','Case_Type']).count().rename(columns={'CPF_Number':'num_cases'})['num_cases']
penalties_ir

penalties_ir.loc[penalties_ir['Proposed_Penalties'] > 0.0].index 

#plot 
plt.figure()
g = sns.FacetGrid(penalties_ir['num_cases'].reset_index(['Opened_Year','Case_Type']), col='Case_Type', hue='Case_Type')
g.map(sns.lineplot, 'Opened_Year', 'num_cases')

plt.show()

#plot the top ten operators by number of penalties with incident reports

#create a df summarizing the penalties by operator 
penalty_by_owner_ir = incident_reports.groupby('Operator_Name').sum()[['Proposed_Penalties', 'Assessed_Penalties','Collected_Penalties']]
cases_by_owner_ir = incident_reports.groupby('Operator_Name').count()[['Proposed_Penalties']].rename(columns={'Proposed_Penalties':'Number_of_Penalties'})
penalty_by_owner_ir = penalty_by_owner_ir.merge(cases_by_owner_ir, on='Operator_Name')

# keep Operator_Name in columns
plot_data = penalty_by_owner_ir.sort_values(by='Number_of_Penalties', ascending=False).head(10)

plot_data = (
    plot_data.rename(columns={
        'Proposed_Penalties': 'Proposed',
        'Assessed_Penalties': 'Assessed',
        'Collected_Penalties': 'Collected',
        'Number_of_Penalties': 'Number'
    })
    .reset_index() 
    .reindex(columns=['Operator_Name','Proposed','Assessed','Collected'])
)

plot_data.columns.name = 'penalty_type'

# organize data
plot_data = plot_data.melt(id_vars="Operator_Name", 
                           var_name="penalty_type", 
                           value_name="value")
plot_data['value'] = plot_data['value'].astype(int)

# plot
plt.figure()
fig, ax = plt.subplots(figsize=(4, 7))
sns.barplot(
    data=plot_data,
    x='Operator_Name',
    y='value',
    hue='penalty_type',
    ax=ax
)

ax.set_ylabel('Penalty Amount, Dollars', fontsize=14)
ax.set_xlabel('',fontsize=14)
fig.suptitle('Penalties by Operator for Cases with Incident Reports\nTop 10 Operators Ranked by Number of Penalty Cases')
ax.ticklabel_format(style='plain', axis='y')
ax.tick_params(axis='x', labelrotation=90)
plt.legend(title='Penalty Type')
plt.tight_layout()
plt.show()

#plots show up a little clunky in vscode... have to work on this!

#load pdfs after scraping here - could use the data frames above to filter for pdfs of interest after scraping

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
folder = r"pdf"
df = process_pdfs_in_folder(folder)
print(df)
#df.to_csv("inspected_locations.csv", index=False)


