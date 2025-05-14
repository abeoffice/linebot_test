from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    QuickReply, QuickReplyButton, PostbackAction, PostbackEvent
)
from dotenv import load_dotenv
import os
import sqlite3, json
from datetime import datetime

# --- DB 初期化 ---
DB = 'data.db'
def init_db():
    with sqlite3.connect(DB) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users
                       (user_id TEXT PRIMARY KEY, industry TEXT)""")
        con.execute("""
            CREATE TABLE IF NOT EXISTS grants (
              id         TEXT PRIMARY KEY,
              title      TEXT,
              url        TEXT,
              start_date TEXT
            )
        """)
init_db()

# --- 業種リスト & Quick Reply ボタン ---
IND_LIST = ["製造業", "IT", "飲食", "建設", "医療", "小売"]
def quick_reply_industries():
    buttons = [
        QuickReplyButton(
            action=PostbackAction(
                label=ind,
                data=json.dumps({"type":"set_industry","value":ind})
            )
        )
        for ind in IND_LIST
    ]
    return QuickReply(items=buttons)

# --- 今日以降の公募を取得する関数 ---
def get_today_grants():
    today = datetime.today().strftime("%Y-%m-%d")
    with sqlite3.connect(DB) as con:
        cur = con.execute(
            "SELECT title FROM grants WHERE start_date >= ? ORDER BY start_date LIMIT 5",
            (today,)
        )
        return [row[0] for row in cur.fetchall()]

# --- 環境変数読み込み & Flask 初期化 ---
load_dotenv()
app = Flask(__name__)
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# --- メッセージ受信ハンドラ ---
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text

    if msg in ["登録", "業種登録"]:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="あなたの業種を選択してください",
                quick_reply=quick_reply_industries()
            )
        )

    elif msg == "今日の補助金":
        grants = get_today_grants()
        if grants:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="本日以降に開始される公募です：\n" +
                         "\n".join(f"・{g}" for g in grants)
                )
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="現在、公募開始予定の補助金は見つかりませんでした。")
            )

    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"あなたが送ったメッセージ: {msg}")
        )

# --- Postback 受信（業種登録） ---
@handler.add(PostbackEvent)
def on_postback(event):
    data = json.loads(event.postback.data)
    if data.get("type") == "set_industry":
        with sqlite3.connect(DB) as con:
            con.execute("INSERT OR REPLACE INTO users VALUES (?,?)",
                        (event.source.user_id, data["value"]))
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"業種を『{data['value']}』で登録しました ✅")
        )

# --- Webhook エンドポイント ---
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# --- アプリ起動 ---
if __name__ == "__main__":
    app.run(debug=True, port=5001)


