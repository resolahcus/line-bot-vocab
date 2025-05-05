from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

app = Flask(__name__)

# 將這兩個換成你 LINE Developers 後台的資料
line_bot_api = LineBotApi('0uMFtsFOaREOYpGpB2DNtP2NyoTXhpDZthv9HUMPf63zscZmAVavZ9XBOYFEOI/LZWnhQ8fP559Wh3dC+33LSHRIVCYbL87eFfhH7H8fC18YcU+QGnc9SWGXV+bjv7b53gS3uJVAbv+8sgw/OM1+aAdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('5a3fbc116c88d47dc293ab027027be2f')

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
    app.run()
