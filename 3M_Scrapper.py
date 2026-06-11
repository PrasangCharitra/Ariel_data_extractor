from bs4 import BeautifulSoup
import requests
import csv
import re
from fractions import Fraction
import logging
import re
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# File handler
fh = logging.FileHandler("scraper.log")
fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(fh)

# Console handler
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(ch)

    
def code_spanner(code):
    try:
        return [ch for ch in code]
    except Exception as e:
        logger.error(f"Code spanner failed for '{code}': {e}")
        return []


def extract_html(url):
    try:
        html = requests.get(url, timeout=10)
        html.raise_for_status()
        return BeautifulSoup(html.text, "html.parser")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for {url}: {e}")
        return None


def parse_price_grid(price_grid, i=25):
    results = []
    try:
        if price_grid:
            table = price_grid.find("table")
            if not table:
                logger.warning("No table found in price grid")
                return results

            qty_row = table.find("tr", class_="tableSubHeader")
            if not qty_row:
                logger.warning("No quantity row found in table")
                return results

            quant_row = qty_row.find_all("td")
            quantities = [td.get_text(strip=True) for td in quant_row[1:-2]]

            next_row = qty_row.find_next_sibling("tr")
            while next_row and "tableSubHeader" not in next_row.get("class", []):
                tds = next_row.find_all("td", {"align": "center"})
                if len(tds) > 1:
                    prices = [td.get_text(strip=True) for td in tds[0:-2]]
                    try:
                        code = code_spanner(tds[-1].get_text(strip=True))
                    except IndexError:
                        logger.warning("Code cell missing in row")
                        code = []
                    if prices:
                        tag = next_row.find("td").get_text(strip=True)
                        results.append({
                            "tag": f"{tag}_{i}-sheets",
                            "quantities": quantities,
                            "prices": prices,
                            "code": code
                        })
                next_row = next_row.find_next_sibling("tr")
    except Exception as e:
        logger.error(f"Price grid parsing failed: {e}")
    return results


def get_sheets(soup):
    sheets = []
    try:
        radios = soup.find_all("input", {"type": "radio", "name": "productForm:j_id_8i"})
        for radio in radios:
            label = soup.find("label", {"for": radio["id"]}).get_text(strip=True)
            sheets.append(label.split("-")[0])
    except Exception as e:
        logger.error(f"Sheet extraction failed: {e}")
    return sheets


def fetch_price_grid(url, i=None):
    try:
        new_soup = extract_html(url)
        if not new_soup:
            return []
        price_grid = new_soup.find("div", {"id": "productForm:priceGrid"})
        if not price_grid:
            logger.warning(f"No price grid found at {url}")
            return []
        return parse_price_grid(price_grid, i) if i else parse_price_grid(price_grid)
    except Exception as e:
        logger.error(f"Fetching price grid failed for {url}: {e}")
        return []


def process_row(row, writer):
    try:
        soup = extract_html(row["prod_page_url"])
        if not soup:
            return

        sheets = get_sheets(soup)
        values = []

        if len(sheets) == 0:
            values.extend(fetch_price_grid(row["prod_page_url"]))
        else:
            for i in sheets:
                new_url = f'{row["prod_page_url"]}?sheets={i}'
                values.extend(fetch_price_grid(new_url, i))



        for row_data in values:
            prices = row_data["prices"]
            quantities = row_data["quantities"]
            codes = row_data["code"]

            # ✅ Filter numeric prices and their corresponding quantities
            numeric_pairs = [
                (qty, price)
                for qty, price in zip(quantities, prices)
                if re.search(r"\d", price)  # keep only prices with digits
            ]

            for idx, (qty, price) in enumerate(numeric_pairs):
                if len(row_data["code"]) == 1:
                    code_val = row_data["code"][0]
                else:
                    try:
                        code_val = row_data["code"][idx]
                    except IndexError:
                        logger.warning(f"Code missing for {row_data['tag']} at index {idx}")
                        code_val = ""
                record = {
                    **row,
                    "Group_name": row_data["tag"],
                    "quantity": qty,
                    "price": price,
                    "code": code_val
                }
                logger.debug(f"Writing record: {record}")
                writer.writerow(record)
                logger.info(f"Processed record: {record}")
    except Exception as e:
        logger.error(f"Price grid parsing failed: {e}")
  


def main():
    try:
        with open("3M_Marketing.csv", newline="", encoding="utf-8") as infile, \
             open("3M_prices2.csv", "w", newline="", encoding="utf-8", buffering=1) as outfile:

            reader = csv.DictReader(infile)
            fieldnames = list(reader.fieldnames) + ["Group_name", "quantity", "price", "code"]
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                process_row(row, writer)

        logger.info("✅ Products with dimensions extracted and saved")
    except Exception as e:
        logger.critical(f"Main execution failed: {e}")


if __name__ == "__main__":
    main()
