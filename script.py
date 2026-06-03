from bs4 import BeautifulSoup
import requests
import pandas as pd
import csv
def string_flattener(s):
    code = ""
    i = 0
    while i < len(s):
        num = 0
        # collect digits
        while i < len(s) and s[i].isdigit():
            num = num * 10 + int(s[i])
            i += 1
        # collect letters and repeat them
        while i < len(s) and not s[i].isdigit():
            code += s[i] * num
            i += 1
    return code

results=[]
data_file = pd.read_csv("data.csv")
for _, data in data_file.iloc[2653:].iterrows():
    html= requests.get(data["prod_page_url"])
    soup = BeautifulSoup(html.text, "html.parser")
    div=soup.select_one("#productDetail")
    if not div:
        continue
    table=div.select("table.pricetable" )
    table_code_header = div.select("table.pricetable th.price-grid-price-label" )
    code_string = table_code_header[0].get_text(strip=True) if table_code_header else None
    start = code_string.find("(") + 1   
    end = code_string.find(")") 
    main_code = code_string[start:end]
    main_string = string_flattener(main_code)
    quantity_list = [th.get_text(strip=True) for th in table[0].select("thead th.tabletext-300")]
    price_list = [td.get_text(strip=True) for td in table[0].select("tbody th.tabletext-300")]
    print(price_list)
    for i, (q, p) in enumerate(zip(quantity_list, price_list)):
        code_char = main_string[i] if main_string and i < len(main_string) else None
        row_out = {
            "Product_name": data["product_name"],
            "Manu_sku": data["manu_sku"],
            "URL": data["prod_page_url"],
            "Quantity": q,
            "Price": p,
            "Price_code": code_char
        }
        # results.append(row_out)
        # print("result appended", row_out)
        with open("products_with_prices.csv", "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=row_out.keys())
                writer.writerow(row_out)
                print("result appended", row_out)
    
# df_out = pd.DataFrame(results)
# df_out.to_csv("products_with_prices.csv", index=False, encoding="utf-8")

print("✅ Pricing grid with codes extracted")