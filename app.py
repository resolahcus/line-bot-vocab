import os
from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

app = Flask(__name__)

# 從環境變數中取得 LINE Channel 的認證
line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))

# 用來紀錄詞彙次數的字典
vocab_counter = {}

@app.route("/callback", methods=['POST'])
def callback():
    # 獲取 X-Line-Signature 頭部資訊，並取得請求的 body
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    # 驗證請求的簽名
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return 'Invalid signature', 400

    return 'OK'

# 當接收到文字訊息時，處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()

    # 處理 "!統計" 指令
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
    # 啟動 Flask 伺服器
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
