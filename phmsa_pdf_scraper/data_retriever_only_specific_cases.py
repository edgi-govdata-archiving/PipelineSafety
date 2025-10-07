import requests
import time
from pathlib import Path

BASE_URL = "https://primis.phmsa.dot.gov/enforcement-data/page-data/case/{}/page-data.json"
PDF_URL = "https://primis.phmsa.dot.gov/enforcement-documents/{}/{}"

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; MyScraper/1.0)"
}

def download_pdf(url, filepath, overwrite=False):
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    if filepath.exists() and not overwrite:
        print(f"   Skipping existing PDF: {filepath.name}")
        return
    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print(f"   Downloaded: {filepath.name}")

# Ask user for comma-separated case codes
case_input = input("Enter case codes separated by commas: ").strip()
case_codes = [c.strip() for c in case_input.split(",") if c.strip()]

# Ask user if they want to overwrite existing PDFs
overwrite_existing = input("Replace existing PDFs if they exist? (Y/N): ").strip().lower() == "y"

for i, cpf in enumerate(case_codes, start=1):
    case_folder = Path("phmsa_pdfs") / cpf
    url = BASE_URL.format(cpf)

    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        detail_json = r.json()
        documents = detail_json["result"]["pageContext"]["caseDocuments"]

        print(f"[{i}/{len(case_codes)}] Case {cpf}: {len(documents)} documents found")
        for doc in documents:
            pdf_url = PDF_URL.format(cpf, doc["name"])
            download_pdf(pdf_url, case_folder / doc["name"], overwrite=overwrite_existing)
            time.sleep(0.2)  # polite delay
    except Exception as e:
        print(f"[{i}/{len(case_codes)}] Failed to fetch case {cpf}: {e}")
