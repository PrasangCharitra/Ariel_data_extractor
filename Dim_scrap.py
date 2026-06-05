from bs4 import BeautifulSoup
import requests
import pandas as pd
import csv


data_file_main = pd.read_csv("products_with_prices.csv")
data_file=data_file_main.copy(deep=True)
print(data_file.columns)
for i, data in data_file.iterrows():
    html= requests.get(data["URL"])
    soup = BeautifulSoup(html.text, "html.parser")
    div=soup.select_one("#pd-features > div > div:nth-child(2) > section:nth-child(1) > div")
    if not div:
        continue
    dimensions = div.getText(strip=True)
    print(dimensions)
    data_file.at[i, "dimensions"] = dimensions
    print(data_file.loc[i])
    


    

data_file.to_csv("products_with_prices.csv", index=False, encoding="utf-8")

print("✅ Pricing grid with codes extracted")