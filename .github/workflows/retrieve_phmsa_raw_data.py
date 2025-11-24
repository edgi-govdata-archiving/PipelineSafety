import requests
import os

def main():
    url = "https://primis.phmsa.dot.gov/enforcement-documents/PHMSA%20Pipeline%20Enforcement%20Raw%20Data.txt"
    output_dir = os.path.join("phmsa_enforcement_analysis", "Data")
    output_file = os.path.join(output_dir, "PHMSA Pipeline Enforcement Raw Data.txt")

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    print("Downloading data file...")
    response = requests.get(url)
    response.raise_for_status()  # will stop workflow if download fails

    # Save file
    with open(output_file, "wb") as f:
        f.write(response.content)

    print(f"File downloaded and saved to: {output_file}")

if __name__ == "__main__":
    main()
