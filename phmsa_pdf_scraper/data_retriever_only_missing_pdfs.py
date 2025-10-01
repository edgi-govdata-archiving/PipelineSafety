import requests
import time
from pathlib import Path

BASE_URL = "https://primis.phmsa.dot.gov/enforcement-data/page-data/case/{}/page-data.json"
LIST_URL = "https://primis.phmsa.dot.gov/enforcement-data/page-data/cases/page-data.json"
PDF_URL = "https://primis.phmsa.dot.gov/enforcement-documents/{}/{}"

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; MyScraper/1.0)"
}

def download_pdf(url, filepath):
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

# Step 1: Fetch the list of cases
resp = requests.get(LIST_URL, headers=headers, timeout=15)
resp.raise_for_status()
data = resp.json()
cases = data["result"]["data"]["postgres"]["sc_cases"]

print(f"Found {len(cases)} cases to check for missing PDFs")

# Global choice: skip cases with existing folders?
skip_existing = input("Skip cases that already have a folder? (Y/N): ").strip().lower() == "y"

# Step 2: Loop through cases and re-download missing PDFs
for i, case in enumerate(cases, start=1):
    cpf = case["cpfNum"]
    case_folder = Path("phmsa_pdfs") / cpf

    if skip_existing and case_folder.exists():
        print(f"[{i}/{len(cases)}] Skipped {cpf} (folder exists)")
        continue

    url = BASE_URL.format(cpf)
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        detail_json = r.json()
        documents = detail_json["result"]["pageContext"]["caseDocuments"]

        missing = []
        for doc in documents:
            filepath = case_folder / doc["name"]
            if not filepath.exists():
                missing.append(doc)

        if missing:
            print(f"[{i}/{len(cases)}] Case {cpf}: {len(missing)} missing docs")
            for doc in missing:
                pdf_url = PDF_URL.format(cpf, doc["name"])
                try:
                    download_pdf(pdf_url, case_folder / doc["name"])
                    print(f"   Downloaded {doc['name']}")
                except Exception as e:
                    print(f"   Failed {doc['name']}: {e}")
                time.sleep(0.2)
        else:
            print(f"[{i}/{len(cases)}] Case {cpf}: all PDFs present")

    except Exception as e:
        print(f"[{i}/{len(cases)}] Failed to check {cpf}: {e}")
        continue
