import requests
import time
from pathlib import Path

BASE_URL = "https://primis.phmsa.dot.gov/enforcement-data/page-data/case/{}/page-data.json"
LIST_URL = "https://primis.phmsa.dot.gov/enforcement-data/page-data/cases/page-data.json"
PDF_URL = "https://primis.phmsa.dot.gov/enforcement-documents/{}/{}"

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; MyScraper/1.0)"
}

# Step 1: Fetch the list of cases
resp = requests.get(LIST_URL, headers=headers, timeout=15)
resp.raise_for_status()
data = resp.json()

cases = data["result"]["data"]["postgres"]["sc_cases"]

print(f"Found {len(cases)} cases")

# Helper function to download a pdf
def download_pdf(url, filepath):
    headers = {"User-Agent": "Mozilla/5.0"}
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)  # ensure subfolders exist
    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


# Step 2: Loop through cases and fetch detail JSON
for i, case in enumerate(cases, start=1):
    cpf = case["cpfNum"]
    url = BASE_URL.format(cpf)
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        detail_json = r.json()
        print(f"[{i}/{len(cases)}] Retrieved {cpf}: {len(detail_json["result"]["pageContext"]["caseDocuments"])} documents to download")
        # Access list of case documents and download each one into folder.
        for document_info in detail_json["result"]["pageContext"]["caseDocuments"]:
            download_pdf(PDF_URL.format(cpf, document_info["name"]), Path("phmsa_pdfs") / cpf / document_info["name"])
    except Exception as e:
        print(f"[{i}/{len(cases)}] Failed {cpf}: {e}")
    time.sleep(0.2)  # delay in case endpoint is unhappy with frequency of requests

