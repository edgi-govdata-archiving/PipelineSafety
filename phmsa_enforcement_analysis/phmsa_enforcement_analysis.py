import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import date
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

import pandas as pd
import matplotlib.pyplot as plt

# ------------------------------
# LOAD DATA
# ------------------------------
phmsa = pd.read_csv(
    r"phmsa_enforcement_analysis/Data/PHMSA Pipeline Enforcement Raw Data.txt",
    sep="\t",
    encoding="latin1"
)

phmsa["Opened_Date"] = pd.to_datetime(phmsa["Opened_Date"])


phmsa["Year"] = phmsa["Opened_Date"].dt.year

#Count
case_counts = (
    phmsa
    .groupby(["Year", "Case_Type"])
    .size()
    .reset_index(name="Count")
)

# Pivot to stacked format
stacked = (
    case_counts
    .pivot(index="Year", columns="Case_Type", values="Count")
    .fillna(0)
)

# Order case types by total count (highest first)
order = (
    stacked.sum(axis=0)
    .sort_values(ascending=False)
    .index
)

# Reorder columns
stacked_ordered = stacked[order]

stacked_ordered.plot(
    kind="bar",
    stacked=True,
    figsize=(11, 6),
    colormap="crest"
)

plt.title("Total Annual PHMSA Enforcement Cases by Case Type")
plt.xlabel("Year")
plt.ylabel("Number of Cases")
plt.legend(title="Case Type", bbox_to_anchor=(1.02, 1), loc="upper left")
plt.tight_layout()
save_plt_as_image(plt.gca().get_title())

plt.show()
