import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import calendar
import os

output_dir = os.path.join("phmsa_enforcement_analysis", "Images")
# Create Images folder if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

def save_plt_as_image(plt_title):
    # Remove unsafe filename characters
    safe_title = "".join(c for c in plt_title if c.isalnum() or c in " _-")
    output_path = os.path.join(output_dir, safe_title + ".png")
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"Saved '{safe_title}' image to: {output_path}")

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

# Extract year and month
phmsa["Year"] = phmsa["Opened_Date"].dt.year
phmsa["Month"] = phmsa["Opened_Date"].dt.month

# ------------------------------
# DEFINE ADMIN PERIODS
# ------------------------------'
# latest_date is dependent on latest available data.
latest_date = phmsa["Opened_Date"].max()
current_inauguration = pd.Timestamp("2025-01-20")
start_period = current_inauguration.to_period("M")
end_period = latest_date.to_period("M")
biden_start, biden_end = pd.Timestamp("2021-01-20"), pd.Timestamp(year=latest_date.year - 4, month=latest_date.month, day=1) + pd.offsets.MonthEnd(0)
trump_start, trump_end = current_inauguration, pd.Timestamp(year=latest_date.year, month=latest_date.month, day=1) + pd.offsets.MonthEnd(0)

# Filter
phmsa_biden = phmsa[(phmsa["Opened_Date"] >= biden_start) & (phmsa["Opened_Date"] <= biden_end)].copy()
phmsa_trump = phmsa[(phmsa["Opened_Date"] >= trump_start) & (phmsa["Opened_Date"] <= trump_end)].copy()

# Add president labels
phmsa_biden["President"] = "Biden 2021"
phmsa_trump["President"] = "Trump 2025"

# Combine
phmsa_filtered = pd.concat([phmsa_biden, phmsa_trump], ignore_index=True)

# ------------------------------
# SETTINGS
# ------------------------------
num_months = (end_period - start_period).n + 1
month_range = range(1, num_months + 1)
custom_palette = {"Biden 2021": "#1f77b4", "Trump 2025": "#d62728"}
month_labels = [f"{i}\n{calendar.month_abbr[i]}" for i in month_range]

# ------------------------------
# HELPER TO FILL MISSING MONTHS
# ------------------------------
def add_missing_months(df, value_col):
    months = pd.DataFrame({"Month": month_range})
    df = months.merge(df, on="Month", how="left").fillna({value_col: 0})
    return df

# ------------------------------
# CASES OPENED PER MONTH
# ------------------------------
monthly_counts = phmsa_filtered.groupby(["President", "Month"]).size().reset_index(name="Count")

# Fill missing months and plot
filled_counts = pd.concat([
    add_missing_months(monthly_counts[monthly_counts["President"]=="Biden 2021"], "Count").assign(President="Biden 2021"),
    add_missing_months(monthly_counts[monthly_counts["President"]=="Trump 2025"], "Count").assign(President="Trump 2025")
])

sns.lineplot(
    data=filled_counts,
    x="Month",
    y="Count",
    hue="President",
    palette=custom_palette,
    marker="o"
)
plt_title = f"PHMSA Enforcement Cases Opened: First {num_months} Months of Term"
plt.title(plt_title)
plt.xlabel("Month")
plt.ylabel("Number of Cases Opened")
plt.xticks(month_range, labels=month_labels)
plt.ylim(0, None)
save_plt_as_image(plt_title)
plt.show()

# ------------------------------
# COLLECTED PENALTIES PER MONTH
# ------------------------------
monthly_collected = phmsa_filtered.groupby(["President", "Month"])["Collected_Penalties"].sum().reset_index()

filled_collected = pd.concat([
    add_missing_months(monthly_collected[monthly_collected["President"]=="Biden 2021"], "Collected_Penalties").assign(President="Biden 2021"),
    add_missing_months(monthly_collected[monthly_collected["President"]=="Trump 2025"], "Collected_Penalties").assign(President="Trump 2025")
])

sns.lineplot(
    data=filled_collected,
    x="Month",
    y="Collected_Penalties",
    hue="President",
    palette=custom_palette,
    marker="o"
)
plt_title = f"PHMSA Collected Penalties: First {num_months} Months of Term"
plt.title(plt_title)
plt.xlabel("Month")
plt.ylabel("Total Collected Penalties ($)")
plt.xticks(month_range, labels=month_labels)
plt.ylim(0, None)
save_plt_as_image(plt_title)
plt.show()

# ------------------------------
# PENALTY COMPARISON (Proposed, Assessed, Collected)
# ------------------------------
penalties = phmsa_filtered.groupby(["President", "Month"])[["Proposed_Penalties","Assessed_Penalties","Collected_Penalties"]].sum().reset_index()

# Ensure missing months are zero
def fill_penalty_months(df, president):
    months = pd.DataFrame({"Month": month_range})
    df = months.merge(df, on="Month", how="left").fillna(0)
    df["President"] = president
    return df

biden_penalties = fill_penalty_months(penalties[penalties["President"]=="Biden 2021"], "Biden 2021")
trump_penalties = fill_penalty_months(penalties[penalties["President"]=="Trump 2025"], "Trump 2025")

penalties_long = pd.concat([biden_penalties, trump_penalties], ignore_index=True).melt(
    id_vars=["President", "Month"],
    value_vars=["Proposed_Penalties","Assessed_Penalties","Collected_Penalties"],
    var_name="Penalty_Type",
    value_name="Amount"
)

# Plot
fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
for ax, pres in zip(axes, ["Biden 2021", "Trump 2025"]):
    subset = penalties_long[penalties_long["President"]==pres]
    sns.lineplot(
        data=subset,
        x="Month",
        y="Amount",
        hue="Penalty_Type",
        marker="o",
        ax=ax,
        #clip_on=False
    )
    ax.set_title(pres)
    ax.set_xticks(month_range)
    ax.set_xticklabels(month_labels)
    ax.set_ylabel("Penalty Amount ($)")
    ax.set_ylim(0, None)
    ax.legend(title="Penalty Type")

plt_title = "Monthly Penalties: Proposed, Assessed, Collected"
plt.suptitle(plt_title, fontsize=16)
plt.tight_layout(rect=[0,0,1,0.95])
save_plt_as_image(plt_title)
plt.show()

#------------------------------------------------------------------------------------
# FREQUENCY OF INCIDENT REPORTS
#------------------------------------------------------------------------------------
# Filter valid reports
phmsa_valid = phmsa_filtered[phmsa_filtered["Report_Type"].notna() & (phmsa_filtered["Report_Type"] != "")]

# Group by president/year/month
monthly_cases = (
    phmsa_valid.groupby(["President", "Year", "Month"])
    .size()
    .reset_index(name="Cases")
)

# Ensure all months are represented
all_months = pd.DataFrame({"Month": month_range})
filled_cases_list = []

for president, year in [("Biden 2021", 2021), ("Trump 2025", 2025)]:
    subset = monthly_cases.query("President == @president").copy()
    subset = all_months.merge(subset, on="Month", how="left")
    subset["Cases"] = subset["Cases"].fillna(0)
    subset["President"] = president
    subset["Year"] = year
    filled_cases_list.append(subset)

filled_cases = pd.concat(filled_cases_list, ignore_index=True)

# ------------------------------
# PLOT INCIDENT REPORTS
# ------------------------------
custom_palette = {"Biden 2021": "#1f77b4", "Trump 2025": "#d62728"}
month_labels = [f"{i}\n{calendar.month_abbr[i]}" for i in month_range]

sns.lineplot(
    data=filled_cases,
    x="Month",
    y="Cases",
    hue="President",
    palette=custom_palette,
    marker="o"
)
plt_title = f"PHMSA Cases with Incident Reports: First {num_months} Months of Term"
plt.title(plt_title)
plt.xlabel("Month")
plt.ylabel("Number of Cases")
plt.xticks(ticks=month_range, labels=month_labels)
plt.ylim(0, None)
save_plt_as_image(plt_title)
plt.show()

# ------------------------------
# ROLLING CUMULATIVE PENALTIES
# ------------------------------
monthly_collected = phmsa_filtered.groupby(["President", "Month"])["Collected_Penalties"].sum().reset_index()

filled_collected = pd.concat([
    add_missing_months(monthly_collected[monthly_collected["President"]=="Biden 2021"], "Collected_Penalties").assign(President="Biden 2021"),
    add_missing_months(monthly_collected[monthly_collected["President"]=="Trump 2025"], "Collected_Penalties").assign(President="Trump 2025")
])

filled_collected["Cumulative_Penalties"] = (
    filled_collected
    .groupby("President")["Collected_Penalties"]
    .cumsum()
)

sns.lineplot(
    data=filled_collected,
    x="Month",
    y="Cumulative_Penalties",
    hue="President",
    palette=custom_palette,
    marker="o"
)
plt_title = f"PHMSA Collected Penalties (Cumulative): First {num_months} Months of Term"
plt.title(plt_title)
plt.xlabel("Month")
plt.ylabel("Cumulative Collected Penalties ($)")
plt.xticks(month_range, labels=month_labels)
plt.ylim(0, None)
save_plt_as_image(plt_title)
plt.show()

#---------------------------------
# CUMULATIVE MONTHLY CASES OPENED
# -------------------------------- 
monthly_counts = phmsa_filtered.groupby(["President", "Month"]).size().reset_index(name="Count")

# Fill missing months and plot
filled_counts = pd.concat([
    add_missing_months(monthly_counts[monthly_counts["President"]=="Biden 2021"], "Count").assign(President="Biden 2021"),
    add_missing_months(monthly_counts[monthly_counts["President"]=="Trump 2025"], "Count").assign(President="Trump 2025")
])

filled_counts["Cumulative_Counts"] = (
    filled_counts
    .groupby("President")["Count"]
    .cumsum()
)
sns.lineplot(
    data=filled_counts,
    x="Month",
    y="Cumulative_Counts",
    hue="President",
    palette=custom_palette,
    marker="o"
)
plt_title = f"PHMSA Enforcement Cases Opened (Cumulative): First {num_months} Months of Term"
plt.title(plt_title)
plt.xlabel("Month")
plt.ylabel("Number of Cases Opened (Cumulative)")
plt.xticks(month_range, labels=month_labels)
plt.ylim(0, None)
save_plt_as_image(plt_title)
plt.show()

#------------------------------------------------------------------------------------
# CUMULATIVE INCIDENT REPORTS
#------------------------------------------------------------------------------------
# Filter valid reports
phmsa_valid = phmsa_filtered[phmsa_filtered["Report_Type"].notna() & (phmsa_filtered["Report_Type"] != "")]

# Group by president/year/month
monthly_cases = (
    phmsa_valid.groupby(["President", "Year", "Month"])
    .size()
    .reset_index(name="Cases")
)

# Ensure all months are represented
all_months = pd.DataFrame({"Month": month_range})
filled_cases_list = []

for president, year in [("Biden 2021", 2021), ("Trump 2025", 2025)]:
    subset = monthly_cases.query("President == @president").copy()
    subset = all_months.merge(subset, on="Month", how="left")
    subset["Cases"] = subset["Cases"].fillna(0)
    subset["President"] = president
    subset["Year"] = year
    filled_cases_list.append(subset)

filled_cases = pd.concat(filled_cases_list, ignore_index=True)

filled_cases["Cumulative_Incidents"] = (
    filled_cases
    .groupby("President")["Cases"]
    .cumsum()
)

# ------------------------------
# PLOT CUMULATIVE INCIDENT REPORTS
# ------------------------------
custom_palette = {"Biden 2021": "#1f77b4", "Trump 2025": "#d62728"}
month_labels = [f"{i}\n{calendar.month_abbr[i]}" for i in month_range]

sns.lineplot(
    data=filled_cases,
    x="Month",
    y="Cumulative_Incidents",
    hue="President",
    palette=custom_palette,
    marker="o"
)
plt_title = f"PHMSA Cases with Incident Reports (Cumulative): First {num_months} Months of Term"
plt.title(plt_title)
plt.xlabel("Month")
plt.ylabel("Cumulative Number of Incident Reports")
plt.xticks(ticks=month_range, labels=month_labels)
plt.ylim(0, None)
save_plt_as_image(plt_title)
plt.show()

# ------------------------------
# CUMULATIVE PENALTY COMPARISON
# ------------------------------
penalties = (
    phmsa_filtered
    .groupby(["President", "Month"])[
        ["Proposed_Penalties", "Assessed_Penalties", "Collected_Penalties"]
    ]
    .sum()
    .reset_index()
)

# Fill missing months for each president
def fill_penalty_months(df, president):
    months = pd.DataFrame({"Month": month_range})
    df = months.merge(df, on="Month", how="left").fillna(0)
    df["President"] = president
    return df

biden_penalties = fill_penalty_months(penalties[penalties["President"]=="Biden 2021"], "Biden 2021")
trump_penalties = fill_penalty_months(penalties[penalties["President"]=="Trump 2025"], "Trump 2025")

# Long format
penalties_long = pd.concat([biden_penalties, trump_penalties], ignore_index=True).melt(
    id_vars=["President", "Month"],
    value_vars=["Proposed_Penalties","Assessed_Penalties","Collected_Penalties"],
    var_name="Penalty_Type",
    value_name="Amount"
)

# Cumulative sum
penalties_long["Cumulative"] = (
    penalties_long
    .groupby(["President", "Penalty_Type"])["Amount"]
    .cumsum()
)

# Plot cumulative penalties
fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)

for ax, pres in zip(axes, ["Biden 2021", "Trump 2025"]):
    subset = penalties_long[penalties_long["President"] == pres]
    sns.lineplot(
        data=subset,
        x="Month",
        y="Cumulative",
        hue="Penalty_Type",
        marker="o",
        ax=ax
    )
    ax.set_title(pres)
    ax.set_xticks(month_range)
    ax.set_xticklabels(month_labels)
    ax.set_ylabel("Cumulative Penalty Amount ($)")
    ax.set_ylim(0, None)
    ax.legend(title="Penalty Type")

plt_title = "Cumulative Penalties: Proposed, Assessed, Collected"
plt.suptitle(plt_title, fontsize=16)
plt.tight_layout(rect=[0,0,1,0.95])
save_plt_as_image(plt_title)
plt.show()
