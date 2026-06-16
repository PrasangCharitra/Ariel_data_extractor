from bs4 import BeautifulSoup
import requests
import csv
import re
from fractions import Fraction
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# File handler
fh = logging.FileHandler("dim_scraper_3m.log")
fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(fh)

# Console handler
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(ch)


def parse_fraction(value: str | int) -> float:
    try:
        value = str(value).strip('"')
        if '-' in value: 
            whole, frac = value.split('-')
            return float(whole) + float(Fraction(frac))
        elif '/' in value:  # pure fraction like 1/2
            return float(Fraction(value))
        else:
            return float(value)
    except Exception as e:
        logger.error(f"Fraction parse error for '{value}': {e}")
        return None


def cleaner(dims: str):
    try:
        dims_clean = dims.replace('""', '"')
        parts = re.findall(r'[\d-]+/?\d*', dims_clean)
        Item_Size_Label = re.findall(r'[A-Za-z]+\.?|[A-Za-z]+', dims_clean)
        keywords = [kw for kw in Item_Size_Label if kw.lower() != "x"]
        dimensions = [parse_fraction(p) for p in parts if p]
        return dimensions, keywords
    except Exception as e:
        logger.error(f"Cleaner failed for '{dims}': {e}")
        return [], []


def split_strap_nostrap(text):
    try:
        pattern = r'((?:[\d\-\/"]+\s*x\s*){1,2}[\d\-\/"]+)"(STRAP|NOSTRAP)'
        matches = re.findall(pattern, text)
        return matches
    except Exception as e:       
        logger.error(f"Regex split failed for '{text}': {e}")
        return []


with open("3M_Marketing.csv", newline="", encoding="utf-8") as infile, \
     open("3M_dimensions.csv", "w", newline="", encoding="utf-8", buffering=1) as outfile:

    reader = csv.DictReader(infile)
    fieldnames = list(reader.fieldnames) + ["length", "breadth", "height", "Item_Size_Label", "Original_text"]
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    for row in reader:
        try:
            url = row.get("prod_page_url")
            logger.info(f"Processing URL: {url}")

            # Network request
            try:
                html = requests.get(url, timeout=10)
                html.raise_for_status()
                logger.debug(f"Fetched HTML for {url}, length={len(html.text)}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed for {url}: {e}")
                continue

            # HTML parsing
            soup = BeautifulSoup(html.text, "html.parser")
            div = soup.find("div", {"id":"productForm:j_id_ce:j_id_cl"})
            if not div:
                logger.warning(f"No dimensions div found for {url}")
                continue

            # Find Actual note size dynamically
            dim_li = None
            valid_patterns = [
                    r"actual.*note.*size",          # matches "Actual note size" or "Actual half note size"
                    r"approximate.*notes.*cube.*size",
                    r"approximate.*size"
                ]
            for li in div.select("ul > li"):
                if any(re.search(pattern, li.get_text(strip=True), re.IGNORECASE) for pattern in valid_patterns):
                    dim_li = li
                    break

            if not dim_li:
                logger.warning(f"No 'Actual note size' entry found for {url}")
                continue

            dim_text = dim_li.get_text(strip=True)
            logger.debug(f"Extracted dimension text: {dim_text}")

            main = dim_text.split(":", 1)[1].strip()
            dims, keywords = cleaner(main)
            logger.debug(f"Parsed dims={dims}, keywords={keywords}")

            if not dims:
                logger.error(f"No dimensions parsed for text: {dim_text}")
                continue

            # Safe indexing
            row["length"] = dims[0] if len(dims) > 0 else "none"
            row["breadth"] = dims[1] if len(dims) > 1 else "none"
            row["height"] = dims[2] if len(dims) > 2 else "none"
            row["Item_Size_Label"] = ", ".join(keywords) if keywords else "No Label"
            row["Original_text"] = dim_text

            try:
                writer.writerow(row)
                logger.info(f"✅ Successfully wrote row for {url}")
            except Exception as e:
                logger.error(f"CSV write failed for {url}: {e}")

        except Exception as e:
            logger.exception(f"Unexpected error processing row {row}: {e}")


logger.info("✅ Products with dimensions extracted and saved")
