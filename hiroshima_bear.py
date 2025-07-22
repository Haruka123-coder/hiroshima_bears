import requests
from bs4 import BeautifulSoup
import pdfplumber
import io
import csv
import os
import re
import pandas as pd
import glob

url="https://www.pref.hiroshima.lg.jp/site/wildlife-management/wm-bear-main.html"
req=requests.get(url)
soup=BeautifulSoup(req.content)
a=soup.find_all("a")

# scrape PDF from the page and store into list
pdf_links=[]
for link in a:
    href=link.get("href")
    text=link.get_text()
    head="https://www.pref.hiroshima.lg.jp/"
    if link.get("href") and "目撃件数" in text and "年度" in text:
        # scrape the link and the text of the link
        pdf_links.append((head + href if not href.startswith("http") else href, text.strip()))

def csv_title(title):
    m=re.search(r"(令和[\d元]+年度ツキノワグマ目撃件数)", title)
    base_title=m.group(1) if m else title.split("(")[0]
    cleaned = re.sub(r'[\\/*?:"<>|\r\n]', '_', base_title)
    return cleaned+".csv"

for link, title in pdf_links:
    try:
        response=requests.get(link)
        response.raise_for_status() #check request errors
        pdf_file=io.BytesIO(response.content)

        csv_file_name=csv_title(title)

        file_exists=os.path.isfile(csv_file_name)
        with open(csv_file_name, "a" if file_exists else "w", newline="", encoding="utf-8") as csvfile:
            writer=csv.writer(csvfile)
            if not file_exists:
                writer.writerow(["link", "page", "title"])
            #read and exract from pdf
            with pdfplumber.open(pdf_file) as pdf:
                for i, page in enumerate(pdf.pages):
                    text=page.extract_text()
                    if text:
                        writer.writerow([link, i+1, text.strip()])
    except Exception as e:
        print(f"error: {e}")

def total_bear(csv_file):
    df = pd.read_csv(csv_file, header=None, names=["link", "page", "text"])
    for row in df["text"]:
        for line in str(row).splitlines():
            if line.strip().startswith("県 計"):
                nums = re.findall(r'\d+', line)
                if nums:
                    return int(nums[-1])
    return None

def latest_and_last_total():
    files = glob.glob("令和*年度ツキノワグマ目撃件数.csv")
    def nendo_key(fname):
        m = re.search(r"令和(\d+)年度ツキノワグマ目撃件数", fname)
        return int(m.group(1)) if m else -1
    files.sort(key=nendo_key)
    if len(files) < 2:
        return None, None
    return files[-1], files[-2]

#Compare the total number of bears between latest year and the year before
latest_csv, last_csv = latest_and_last_total()
if latest_csv and last_csv:
    latest_total = total_bear(latest_csv)
    last_total = total_bear(last_csv)
    print(f"{latest_csv}:{latest_total}, {last_csv}:{last_total}")
    if latest_total is not None and last_total is not None:
        if latest_total > last_total:
            print(f"[Notice] This year（{latest_csv}）'s total({latest_total}) has exceeded last year 's ({last_csv})total ({last_total}).")
        else:
            print(f"The total of this year（{latest_csv}）is less than the last year's.")
    else:
        print("Was not able to extract the total.")
else:
    print("There are no data to compare.")