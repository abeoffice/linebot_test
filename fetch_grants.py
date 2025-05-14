# fetch_grants.py

import sqlite3
import requests
from datetime import datetime
from bs4 import BeautifulSoup

DB = "data.db"
JGRANTS_API    = "https://api.jgrants.go.jp/grants"
JGRANTS_RSS    = "https://jgrants.go.jp/rss/open.xml"
JGRANTS_SCRAPE = "https://jgrants.go.jp/openings"

def init_db():
    """ grants テーブルを作成（存在しなければ） """
    with sqlite3.connect(DB) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS grants (
              id         TEXT PRIMARY KEY,
              title      TEXT,
              url        TEXT,
              start_date TEXT
            )
        """)

def fetch_from_jgrants():
    """ 1️⃣ jGrants API から取得 """
    try:
        resp = requests.get(JGRANTS_API, params={"status": "open"}, timeout=10)
        resp.raise_for_status()
        for g in resp.json().get("results", []):
            yield {
                "id":         g["grantId"],
                "title":      g["title"],
                "url":        g["detailUrl"],
                "start_date": g["startDate"][:10]
            }
    except Exception:
        return  # エラー時は空で返す

def fetch_from_rss():
    """ 2️⃣ RSS から取得 """
    try:
        resp = requests.get(JGRANTS_RSS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "xml")
        for item in soup.find_all("item"):
            yield {
                "id":         item.guid.text,
                "title":      item.title.text,
                "url":        item.link.text,
                "start_date": item.pubDate.text.split(" ")[0]
            }
    except Exception:
        return

def fetch_from_scrape():
    """ 3️⃣ Webスクレイピング """
    try:
        resp = requests.get(JGRANTS_SCRAPE, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for entry in soup.select(".grant-entry"):
            gid = entry["data-id"]
            yield {
                "id":         gid,
                "title":      entry.select_one(".title").get_text(strip=True),
                "url":        "https://jgrants.go.jp" + entry.select_one("a")["href"],
                "start_date": entry.select_one(".date").get_text(strip=True)
            }
    except Exception:
        return

def upsert_grants(grants):
    """ DB に INSERT OR REPLACE """
    with sqlite3.connect(DB) as con:
        for g in grants:
            con.execute("""
                INSERT OR REPLACE INTO grants(id, title, url, start_date)
                VALUES (:id, :title, :url, :start_date)
            """, g)

def main():
    init_db()

    # ① API
    grants = list(fetch_from_jgrants())

    # ② API が取れなかったら RSS
    if not grants:
        grants = list(fetch_from_rss())

    # ③ RSS も取れなかったら Scraping
    if not grants:
        grants = list(fetch_from_scrape())

    upsert_grants(grants)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{now} -> {len(grants)} 件を DB に登録しました。")

if __name__ == "__main__":
    main()

