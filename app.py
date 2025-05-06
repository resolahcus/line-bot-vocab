from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError
import os

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))

# 髒話清單
profanities = ["幹", "靠北", "白癡", "你媽", "他媽", "智障"]

# 髒話次數記錄：{ user_id: {"name": 暱稱, "count": 次數} }
profanity_counter = {}

@app.route("/")
def index():
    return "Hello, world!"  # 根路径返回一个简单的消息

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return 'Invalid signature', 400

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    user_id = event.source.user_id

    # 嘗試取得暱稱
    try:
        profile = line_bot_api.get_profile(user_id)
        display_name = profile.display_name
    except:
        display_name = "未知使用者"

    # 處理統計指令
    if text == "!統計":
        if not profanity_counter:
            reply = "目前沒有紀錄"
        else:
            lines = [f"{data['name']}: {data['count']} 次" for data in profanity_counter.values()]
            reply = "髒話使用統計：\n" + "\n".join(lines)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    # 偵測髒話
    if any(word in text for word in profanities):
        if user_id not in profanity_counter:
            profanity_counter[user_id] = {"name": display_name, "count": 1}
        else:
            profanity_counter[user_id]["count"] += 1

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="不要說髒話！"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
