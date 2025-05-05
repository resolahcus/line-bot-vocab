import os
from flask import Flask, request
from linebot.v3 import LineBotApi
from linebot.v3.webhook import WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

app = Flask(__name__)

# 使用新版的 SDK
line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))

# 用來記錄詞彙次數
vocab_counter = {}

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

    if text == "!統計":
        if not vocab_counter:
            reply = "目前沒有紀錄"
        else:
            lines = [f"{word}: {count}" for word, count in vocab_counter.items()]
            reply = "\n".join(lines)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    # 每個詞統計一次
    words = text.split()
    for word in words:
        vocab_counter[word] = vocab_counter.get(word, 0) + 1

if __name__ == "__main__":
    app.run(debug=True)
