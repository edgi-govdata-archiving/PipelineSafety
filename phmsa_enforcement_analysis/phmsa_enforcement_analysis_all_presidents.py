import matplotlib
import pandas as pd
from pyfonts import load_google_font
from matplotlib.ticker import ScalarFormatter
import seaborn as sns
import matplotlib.pyplot as plt
import calendar
import numpy as np
import os
import datetime

# ------------------------------
# SETUP: OUTPUT DIRECTORY
# ------------------------------
output_dir = os.path.join("phmsa_enforcement_analysis", "Images", "Historical Comparison")
os.makedirs(output_dir, exist_ok=True)

if os.getenv("GITHUB_ACTIONS"):
    matplotlib.use("Agg")

# ------------------------------
# HELPER: SAVE PLOT AS IMAGE
# ------------------------------
def save_plt_as_image(plt_title):
    # Remove unsafe filename characters
    safe_title = "".join(c for c in plt_title if c.isalnum() or c in " _-")
    output_path = os.path.join(output_dir, safe_title + ".png")
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"Saved '{safe_title}' image to: {output_path}")
    if not os.getenv("GITHUB_ACTIONS"):
        plt.show()
    plt.close()

# ------------------------------
# LOAD DATA
# ------------------------------
phmsa = pd.read_csv(
    r"phmsa_enforcement_analysis/Data/PHMSA Pipeline Enforcement Raw Data.txt",
    sep="\t",
    encoding="latin1"
)

# Convert Opened_Date to datetime
phmsa["Opened_Date"] = pd.to_datetime(phmsa["Opened_Date"], errors="coerce")

# Extract year (keep for reference)
phmsa["Year"] = phmsa["Opened_Date"].dt.year

# ------------------------------
# DYNAMIC DATE CALCULATION
# ------------------------------
latest_date = phmsa["Opened_Date"].max()

# Calculate the last complete month based on runtime date
today = datetime.date.today()
if today.month == 1:
    last_complete = pd.Timestamp(today.year - 1, 12, 31)
else:
    last_complete = pd.Timestamp(today.year, today.month - 1, 1) + pd.offsets.MonthEnd(0)

# Define Trump 2025 analysis period
trump_start = pd.Timestamp("2025-01-20")
trump_end = min(last_complete, latest_date)

# Calculate number of months for Trump 2025 (used for aligning all presidents)
num_months = (trump_end.year - trump_start.year) * 12 + (trump_end.month - trump_start.month) + 1

custom_palette = {"Historical Average": "#1f77b4", "Trump 2025": "#d62728"}

# ------------------------------
# HISTORICAL AVERAGE CALCULATION
# ------------------------------
# Define presidential terms (start date, actual data start date)
# Note: Bush term started 2001, but data only available from 2002
presidential_terms = [
    {"name": "Bush", "start": pd.Timestamp("2001-01-20"), "data_start": pd.Timestamp("2002-01-01")},
    {"name": "Obama", "start": pd.Timestamp("2009-01-20"), "data_start": pd.Timestamp("2009-01-20")},
    {"name": "Trump I", "start": pd.Timestamp("2017-01-20"), "data_start": pd.Timestamp("2017-01-20")},
    {"name": "Biden", "start": pd.Timestamp("2021-01-20"), "data_start": pd.Timestamp("2021-01-20")},
]

# Calculate end dates for each term (N months from start)
for term in presidential_terms:
    term["end"] = term["start"] + pd.DateOffset(months=num_months - 1) + pd.offsets.MonthEnd(0)

# Filter data for each previous president (first N months of their term)
previous_presidents_data = []
for term in presidential_terms:
    # Use max of term start and data availability start
    actual_start = max(term["start"], term["data_start"])
    term_data = phmsa[(phmsa["Opened_Date"] >= actual_start) & 
                      (phmsa["Opened_Date"] <= term["end"])].copy()
    
    if len(term_data) > 0:
        # Calculate month-in-term (1-indexed)
        term_data["Month"] = ((term_data["Opened_Date"].dt.year - term["start"].year) * 12 + 
                              (term_data["Opened_Date"].dt.month - term["start"].month) + 1)
        term_data["President"] = term["name"]
        previous_presidents_data.append(term_data)

# Filter Trump 2025 data
phmsa_trump2025 = phmsa[(phmsa["Opened_Date"] >= trump_start) & 
                         (phmsa["Opened_Date"] <= trump_end)].copy()
phmsa_trump2025["Month"] = ((phmsa_trump2025["Opened_Date"].dt.year - trump_start.year) * 12 + 
                             (phmsa_trump2025["Opened_Date"].dt.month - trump_start.month) + 1)
phmsa_trump2025["President"] = "Trump 2025"

# Calculate HISTORICAL AVERAGE with dynamic president count per month
if previous_presidents_data:
    all_prev_data = pd.concat(previous_presidents_data, ignore_index=True)
    
    # Helper function to calculate average with variable number of presidents per month
    def calculate_historical_average(df, value_cols):
        """
        For each month-in-term, calculate average across presidents that have data.
        Returns a DataFrame with Month, President='Historical Average', and averaged value_cols.
        """
        # Group by President and Month, sum the values
        grouped = df.groupby(["President", "Month"])[value_cols].sum().reset_index()
        
        # For each month, average across all presidents that have data for that month
        result_rows = []
        for month in range(1, num_months + 1):
            month_data = grouped[grouped["Month"] == month]
            if len(month_data) > 0:
                avg_row = {"Month": month, "President": "Historical Average"}
                for col in value_cols:
                    avg_row[col] = month_data[col].mean()
                result_rows.append(avg_row)
        
        return pd.DataFrame(result_rows)
    
    # Create averaged dataset for comparisons
    historical_avg = calculate_historical_average(all_prev_data, 
                                                   ["Proposed_Penalties", "Assessed_Penalties", 
                                                    "Collected_Penalties"])
    
    # For counts, handle separately with same logic
    counts_grouped = all_prev_data.groupby(["President", "Month"]).size().reset_index(name="Count")
    count_avg_rows = []
    for month in range(1, num_months + 1):
        month_data = counts_grouped[counts_grouped["Month"] == month]
        if len(month_data) > 0:
            count_avg_rows.append({
                "Month": month, 
                "President": "Historical Average",
                "Count": month_data["Count"].mean()
            })
    avg_counts = pd.DataFrame(count_avg_rows)
    
else:
    historical_avg = pd.DataFrame()
    avg_counts = pd.DataFrame()

# ------------------------------
# MONTH RANGE AND LABELS
# ------------------------------
month_range = range(1, num_months + 1)
# Create dynamic labels (e.g., "1 Jan", "2 Feb"...)
month_labels = []
for i in month_range:
    month_idx = (trump_start.month + i - 2) % 12 + 1
    month_labels.append(f"{i}\n{calendar.month_abbr[month_idx]}")

# ------------------------------
# SETTINGS
# ------------------------------
# Simple list versions of the gradients, which we can use for seaborn color palettes:
bicolor_standard_list = ["#19659e", "#dbbe48", "#A74956"]
sns.set_theme(style="whitegrid", palette=bicolor_standard_list)

# ------------------------------
# FONT SETTINGS
# ------------------------------

# Get Mona Sans font from Google Fonts. 
# URL: https://fonts.google.com/specimen/Mona+Sans
font_path_regular = load_google_font("Mona Sans", weight='regular')
font_path_bold = load_google_font("Mona Sans", weight='bold')
matplotlib.font_manager.fontManager.addfont(font_path_regular.get_file())
matplotlib.font_manager.fontManager.addfont(font_path_bold.get_file())

# Helper function to set matplotlib fonts to our chosen font. This needs to be called AFTER sns.set_theme() is called,
# hence this helper function to make that quick every time we graph something.
def set_matplotlib_font(style = "regular"):
    plt.rcParams["font.family"] = 'sans-serif'
    if style == "regular":
        plt.rcParams["font.sans-serif"] = font_path_regular.get_name()
        sns.set_context("notebook", rc={"font.family": font_path_regular.get_name()})
    elif style == "bold":
        plt.rcParams["font.sans-serif"] = font_path_bold.get_name()
        sns.set_context("notebook", rc={"font.family": font_path_bold.get_name()})

set_matplotlib_font("regular")

# ------------------------------
# HELPER TO FILL MISSING MONTHS
# ------------------------------
def add_missing_months(df, value_col):
    months = pd.DataFrame({"Month": month_range})
    df = months.merge(df, on="Month", how="left").fillna({value_col: 0})
    return df

def fill_penalty_months(df, president):
    months = pd.DataFrame({"Month": month_range})
    df = months.merge(df, on="Month", how="left").fillna(0)
    df["President"] = president
    return df

# ------------------------------
# CASES OPENED PER MONTH
# ------------------------------
# Historical average counts
if not avg_counts.empty:
    avg_counts_filled = add_missing_months(avg_counts, "Count")
else:
    # Create empty dataframe with all months
    avg_counts_filled = pd.DataFrame({"Month": month_range, "Count": 0, "President": "Historical Average"})

# Trump 2025 counts
monthly_counts_trump = phmsa_trump2025.groupby("Month").size().reset_index(name="Count")
monthly_counts_trump["President"] = "Trump 2025"
trump_counts_filled = add_missing_months(monthly_counts_trump, "Count")
trump_counts_filled["President"] = "Trump 2025"

# Combine
filled_counts = pd.concat([avg_counts_filled, trump_counts_filled], ignore_index=True)

# Plot
sns.lineplot(
    data=filled_counts,
    x="Month",
    y="Count",
    hue="President",
    palette=custom_palette,
    marker="o"
)
plt_title = f"PHMSA Enforcement Cases Opened Since Inauguration: Historical Average vs Trump 2025"
plt.title(plt_title)
plt.xlabel("Month")
plt.ylabel("Number of Cases Opened")
plt.xticks(month_range, labels=month_labels)
plt.ylim(0, None)
save_plt_as_image(plt_title)

# ------------------------------
# COLLECTED PENALTIES PER MONTH
# ------------------------------
# Historical average collected penalties
if not historical_avg.empty:
    avg_collected = historical_avg[["Month", "Collected_Penalties"]].copy()
    avg_collected_filled = add_missing_months(avg_collected, "Collected_Penalties")
    avg_collected_filled["President"] = "Historical Average"
else:
    avg_collected_filled = pd.DataFrame({"Month": month_range, "Collected_Penalties": 0, "President": "Historical Average"})

# Trump 2025 collected penalties
monthly_collected_trump = phmsa_trump2025.groupby("Month")["Collected_Penalties"].sum().reset_index()
monthly_collected_trump["President"] = "Trump 2025"
trump_collected_filled = add_missing_months(monthly_collected_trump, "Collected_Penalties")
trump_collected_filled["President"] = "Trump 2025"

# Combine
filled_collected = pd.concat([avg_collected_filled, trump_collected_filled], ignore_index=True)

# Plot
sns.lineplot(
    data=filled_collected,
    x="Month",
    y="Collected_Penalties",
    hue="President",
    palette=custom_palette,
    marker="o"
)
plt_title = f"PHMSA Collected Penalties Since Inauguration: Historical Average vs Trump 2025"
plt.title(plt_title)
plt.xlabel("Month")
plt.ylabel("Total Collected Penalties ($)")
plt.xticks(month_range, labels=month_labels)
plt.ylim(0, None)
save_plt_as_image(plt_title)

# ------------------------------
# PENALTY COMPARISON (Proposed, Assessed, Collected)
# ------------------------------
# Historical average penalties
if not historical_avg.empty:
    avg_penalties_filled = fill_penalty_months(historical_avg, "Historical Average")
else:
    # Create empty dataframe with all months
    months = pd.DataFrame({"Month": month_range})
    avg_penalties_filled = months.assign(
        Proposed_Penalties=0,
        Assessed_Penalties=0,
        Collected_Penalties=0,
        President="Historical Average"
    )

# Trump 2025 penalties
penalties_trump = phmsa_trump2025.groupby("Month")[["Proposed_Penalties","Assessed_Penalties","Collected_Penalties"]].sum().reset_index()
trump_penalties_filled = fill_penalty_months(penalties_trump, "Trump 2025")

# Combine and melt for plotting
penalties_long = pd.concat([avg_penalties_filled, trump_penalties_filled], ignore_index=True).melt(
    id_vars=["President", "Month"],
    value_vars=["Proposed_Penalties","Assessed_Penalties","Collected_Penalties"],
    var_name="Penalty_Type",
    value_name="Amount"
)

# Plot
fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
for ax, pres in zip(axes, ["Historical Average", "Trump 2025"]):
    subset = penalties_long[penalties_long["President"]==pres]
    sns.lineplot(
        data=subset,
        x="Month",
        y="Amount",
        hue="Penalty_Type",
        marker="o",
        ax=ax,
    )
    ax.set_title(pres)
    ax.set_xticks(month_range)
    ax.set_xticklabels(month_labels)
    ax.set_ylabel("Penalty Amount ($)")
    ax.set_ylim(0, None, auto=True)
    ax.legend(title="Penalty Type")

plt_title = "Monthly Penalties: Proposed, Assessed, Collected Since Inauguration - Historical vs Trump 2025"
plt.suptitle(plt_title, fontsize=16)
plt.tight_layout(rect=[0,0,1,0.95])
save_plt_as_image(plt_title)

#------------------------------------------------------------------------------------
# FREQUENCY OF INCIDENT REPORTS
#------------------------------------------------------------------------------------
# Filter valid reports for Trump 2025
phmsa_valid_trump = phmsa_trump2025[phmsa_trump2025["Report_Type"].notna() & (phmsa_trump2025["Report_Type"] != "")]

# Group by month for Trump 2025
monthly_cases_trump = (
    phmsa_valid_trump.groupby("Month")
    .size()
    .reset_index(name="Cases")
)
monthly_cases_trump["President"] = "Trump 2025"
monthly_cases_trump["Year"] = 2025

# Historical average for incident reports
if previous_presidents_data:
    all_prev_valid = pd.concat(previous_presidents_data, ignore_index=True)
    all_prev_valid = all_prev_valid[all_prev_valid["Report_Type"].notna() & (all_prev_valid["Report_Type"] != "")]
    
    # Group by President and Month
    prev_cases_grouped = all_prev_valid.groupby(["President", "Month"]).size().reset_index(name="Cases")
    
    # Average across presidents for each month
    avg_cases_rows = []
    for month in range(1, num_months + 1):
        month_data = prev_cases_grouped[prev_cases_grouped["Month"] == month]
        if len(month_data) > 0:
            avg_cases_rows.append({
                "Month": month,
                "President": "Historical Average",
                "Cases": month_data["Cases"].mean(),
                "Year": None  # Placeholder
            })
    avg_cases = pd.DataFrame(avg_cases_rows)
else:
    avg_cases = pd.DataFrame()

# Combine and fill missing months
all_months_df = pd.DataFrame({"Month": month_range})

if not avg_cases.empty:
    filled_avg = all_months_df.merge(avg_cases, on="Month", how="left")
    filled_avg["Cases"] = filled_avg["Cases"].fillna(0)
    filled_avg["President"] = "Historical Average"
else:
    filled_avg = all_months_df.assign(Cases=0, President="Historical Average", Year=None)

# Fill Trump 2025 data
filled_trump = all_months_df.merge(monthly_cases_trump, on="Month", how="left")
filled_trump["Cases"] = filled_trump["Cases"].fillna(0)
filled_trump["President"] = "Trump 2025"
filled_trump["Year"] = 2025

# Combine
filled_cases = pd.concat([filled_avg, filled_trump], ignore_index=True)

# Plot
sns.lineplot(
    data=filled_cases,
    x="Month",
    y="Cases",
    hue="President",
    palette=custom_palette,
    marker="o"
)
plt_title = f"PHMSA Cases with Incident Reports Since Inauguration: Historical Average vs Trump 2025"
plt.title(plt_title)
plt.xlabel("Month")
plt.ylabel("Number of Cases")
plt.xticks(ticks=month_range, labels=month_labels)
plt.ylim(0, None)
save_plt_as_image(plt_title)

# ------------------------------
# ROLLING CUMULATIVE PENALTIES
# ------------------------------
# Historical average cumulative
if not historical_avg.empty:
    avg_collected = historical_avg[["Month", "Collected_Penalties"]].copy()
    avg_collected_filled = add_missing_months(avg_collected, "Collected_Penalties")
    avg_collected_filled["President"] = "Historical Average"
else:
    avg_collected_filled = pd.DataFrame({"Month": month_range, "Collected_Penalties": 0, "President": "Historical Average"})

# Trump 2025 cumulative
monthly_collected_trump = phmsa_trump2025.groupby("Month")["Collected_Penalties"].sum().reset_index()
monthly_collected_trump["President"] = "Trump 2025"
trump_collected_filled = add_missing_months(monthly_collected_trump, "Collected_Penalties")
trump_collected_filled["President"] = "Trump 2025"

# Combine
filled_collected = pd.concat([avg_collected_filled, trump_collected_filled], ignore_index=True)

# Calculate cumulative
filled_collected["Cumulative_Penalties"] = (
    filled_collected
    .groupby("President")["Collected_Penalties"]
    .cumsum()
)

# Plot
sns.lineplot(
    data=filled_collected,
    x="Month",
    y="Cumulative_Penalties",
    hue="President",
    palette=custom_palette,
    marker="o"
)
plt_title = f"PHMSA Collected Penalties (Cumulative Since Inauguration): Historical Average vs Trump 2025"
plt.title(plt_title)
plt.xlabel("Month")
plt.ylabel("Cumulative Collected Penalties ($)")
plt.xticks(month_range, labels=month_labels)
plt.ylim(0, None)
save_plt_as_image(plt_title)

#---------------------------------
# CUMULATIVE MONTHLY CASES OPENED
#--------------------------------
# Historical average counts (reuse earlier data)
if not avg_counts.empty:
    avg_counts_filled = add_missing_months(avg_counts, "Count")
else:
    avg_counts_filled = pd.DataFrame({"Month": month_range, "Count": 0, "President": "Historical Average"})

# Trump 2025 counts
monthly_counts_trump = phmsa_trump2025.groupby("Month").size().reset_index(name="Count")
monthly_counts_trump["President"] = "Trump 2025"
trump_counts_filled = add_missing_months(monthly_counts_trump, "Count")
trump_counts_filled["President"] = "Trump 2025"

# Combine
filled_counts = pd.concat([avg_counts_filled, trump_counts_filled], ignore_index=True)

# Calculate cumulative
filled_counts["Cumulative_Counts"] = (
    filled_counts
    .groupby("President")["Count"]
    .cumsum()
)

# Plot
sns.lineplot(
    data=filled_counts,
    x="Month",
    y="Cumulative_Counts",
    hue="President",
    palette=custom_palette,
    marker="o"
)
plt_title = f"PHMSA Enforcement Cases Opened (Cumulative Since Inauguration): Historical Average vs Trump 2025"
plt.title(plt_title)
plt.xlabel("Month")
plt.ylabel("Number of Cases Opened (Cumulative)")
plt.xticks(month_range, labels=month_labels)
plt.ylim(0, None)
save_plt_as_image(plt_title)

#------------------------------------------------------------------------------------
# CUMULATIVE INCIDENT REPORTS
#------------------------------------------------------------------------------------
# Filter valid reports for Trump 2025 (reuse earlier data)
phmsa_valid_trump = phmsa_trump2025[phmsa_trump2025["Report_Type"].notna() & (phmsa_trump2025["Report_Type"] != "")]

# Group by month for Trump 2025
monthly_cases_trump = (
    phmsa_valid_trump.groupby("Month")
    .size()
    .reset_index(name="Cases")
)
monthly_cases_trump["President"] = "Trump 2025"
monthly_cases_trump["Year"] = 2025

# Historical average for incident reports (reuse earlier logic)
if previous_presidents_data:
    all_prev_valid = pd.concat(previous_presidents_data, ignore_index=True)
    all_prev_valid = all_prev_valid[all_prev_valid["Report_Type"].notna() & (all_prev_valid["Report_Type"] != "")]
    prev_cases_grouped = all_prev_valid.groupby(["President", "Month"]).size().reset_index(name="Cases")
    
    avg_cases_rows = []
    for month in range(1, num_months + 1):
        month_data = prev_cases_grouped[prev_cases_grouped["Month"] == month]
        if len(month_data) > 0:
            avg_cases_rows.append({
                "Month": month,
                "President": "Historical Average",
                "Cases": month_data["Cases"].mean(),
                "Year": None
            })
    avg_cases = pd.DataFrame(avg_cases_rows)
else:
    avg_cases = pd.DataFrame()

# Combine and fill missing months
all_months_df = pd.DataFrame({"Month": month_range})

if not avg_cases.empty:
    filled_avg = all_months_df.merge(avg_cases, on="Month", how="left")
    filled_avg["Cases"] = filled_avg["Cases"].fillna(0)
    filled_avg["President"] = "Historical Average"
else:
    filled_avg = all_months_df.assign(Cases=0, President="Historical Average", Year=None)

# Fill Trump 2025 data
filled_trump = all_months_df.merge(monthly_cases_trump, on="Month", how="left")
filled_trump["Cases"] = filled_trump["Cases"].fillna(0)
filled_trump["President"] = "Trump 2025"
filled_trump["Year"] = 2025

# Combine
filled_cases = pd.concat([filled_avg, filled_trump], ignore_index=True)

# Calculate cumulative
filled_cases["Cumulative_Incidents"] = (
    filled_cases
    .groupby("President")["Cases"]
    .cumsum()
)

# Plot
sns.lineplot(
    data=filled_cases,
    x="Month",
    y="Cumulative_Incidents",
    hue="President",
    palette=custom_palette,
    marker="o"
)
plt_title = f"PHMSA Cases with Incident Reports (Cumulative Since Inauguration): Historical Average vs Trump 2025"
plt.title(plt_title)
plt.xlabel("Month")
plt.ylabel("Cumulative Number of Incident Reports")
plt.xticks(ticks=month_range, labels=month_labels)
plt.ylim(0, None)
save_plt_as_image(plt_title)

# ------------------------------
# CUMULATIVE PENALTY COMPARISON
# ------------------------------
# Historical average penalties
if not historical_avg.empty:
    avg_penalties_filled = fill_penalty_months(historical_avg, "Historical Average")
else:
    months = pd.DataFrame({"Month": month_range})
    avg_penalties_filled = months.assign(
        Proposed_Penalties=0,
        Assessed_Penalties=0,
        Collected_Penalties=0,
        President="Historical Average"
    )

# Trump 2025 penalties
penalties_trump = phmsa_trump2025.groupby("Month")[["Proposed_Penalties","Assessed_Penalties","Collected_Penalties"]].sum().reset_index()
trump_penalties_filled = fill_penalty_months(penalties_trump, "Trump 2025")

# Combine and melt
penalties_long = pd.concat([avg_penalties_filled, trump_penalties_filled], ignore_index=True).melt(
    id_vars=["President", "Month"],
    value_vars=["Proposed_Penalties","Assessed_Penalties","Collected_Penalties"],
    var_name="Penalty_Type",
    value_name="Amount"
)

# Calculate cumulative
penalties_long["Cumulative"] = (
    penalties_long
    .groupby(["President", "Penalty_Type"])["Amount"]
    .cumsum()
)

# Plot
fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)

for ax, pres in zip(axes, ["Historical Average", "Trump 2025"]):
    subset = penalties_long[penalties_long["President"] == pres]
    sns.lineplot(
        data=subset,
        x="Month",
        y="Cumulative",
        hue="Penalty_Type",
        marker="o",
        ax=ax
    )
     
    month_labels = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]

    ax.set_title(pres)
    step = 1  # could use something else, like every 3 months

    ticks = np.arange(1, max(month_range) + 1, step)
    labels = [month_labels[(i-1) % 12] for i in ticks]

    ax.set_xticks(ticks)
    ax.set_xticklabels(labels)
    ax.set_title(pres)
    #ax.set_xticks(month_range)
    #ax.set_xticklabels(month_labels)
    ax.set_ylabel("Cumulative Penalty Amount ($)")
    ax.set_ylim(0, None, auto=True)
    ax.legend(title="Penalty Type")


formatter = ScalarFormatter()
formatter.set_scientific(False)
plt.gca().yaxis.set_major_formatter(formatter)

# Format y-axis labels in millions
plt.gca().set_yticklabels([f'${int(y * 1e-6)} Million' for y in plt.gca().get_yticks()])

plt_title = "Cumulative Penalties Since Inauguration: Proposed, Assessed, Collected  - Historical vs Trump 2025"
plt.suptitle(plt_title, fontsize=16)
plt.tight_layout(rect=[0,0,1,0.95])
save_plt_as_image(plt_title)
