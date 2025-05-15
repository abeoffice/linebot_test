# notify_grants.py

import os
import sqlite3
from datetime import date
from dotenv import load_dotenv
from linebot import LineBotApi
from linebot.models import TextSendMessage

# ① .env を読み込む
load_dotenv()
TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

# ② DB ファイルパス
DB = "data.db"

def push_notifications():
    # ③ LineBotApi を初期化
    line_bot_api = LineBotApi(TOKEN)

    # ④ 今日の日付 (YYYY-MM-DD) を取得
    today = date.today().strftime("%Y-%m-%d")

    # ⑤ DB から 「今日開始」×「ユーザー業種」に該当するレコードを JOIN で取得
    with sqlite3.connect(DB) as con:
        sql = """
        SELECT u.user_id, g.title, g.url
        FROM users AS u
        JOIN grants AS g
          ON u.industry = g.industry
        WHERE g.start_date = ?
        """
        rows = con.execute(sql, (today,)).fetchall()

    # ⑥ 取得件数を表示
    print(f"{today} にマッチした件数:", len(rows))

    # ⑦ 各ユーザーにプッシュ
    for user_id, title, url in rows:
        text = f"🔔 {title}\n詳細: {url}"
        line_bot_api.push_message(user_id, TextSendMessage(text=text))
        print("→ 通知:", user_id, title)

    if not rows:
        print("→ 該当ユーザーなし。")

import os
import sqlite3
from datetime import datetime
from linebot import LineBotApi
from linebot.models import TextSendMessage

TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

def push_notifications():
    today = datetime.today().strftime("%Y-%m-%d")
    with sqlite3.connect(DB) as con:
        cur = con.execute("""
          SELECT u.user_id, g.title || '\\n' || g.url AS message
          FROM users AS u
          JOIN grants AS g
            ON u.industry = g.industry
          WHERE g.start_date = ?
        """, (today,))
        rows = cur.fetchall()

    if not rows:
        print(f"{today} にマッチした件数: 0")
        return

    line_bot_api = LineBotApi(TOKEN)
    to_list = [r[0] for r in rows]
    messages = [TextSendMessage(text=r[1]) for r in rows]

    # マルチキャストで一斉通知
    line_bot_api.multicast(to_list, messages)
    print(f"{today} にマッチした件数: {len(rows)} → {len(set(to_list))} ユーザーに通知を送りました。")



if __name__ == "__main__":
    push_notifications()
