from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError
import os
import re

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))

# 單字型髒話：需精準比對（避免幹什麼被誤判）
word_profanities = ["幹", "操", "糙"]
# 片語型髒話：可直接判斷是否出現在句中
phrase_profanities = ["靠北", "靠杯", "靠邀", "靠腰", "幹你娘", "你媽", "他媽", "操你媽", "三小", "啥小", "去你的", "去你媽", "擊敗", "雞掰", "智障", "白癡", "傻逼", "低能", "低能兒", "破麻", "破病", "肏"]

# 髒話次數記錄
profanity_counter = {}

@app.route("/")
def index():
    return "Hello, world!"

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
    user_id = getattr(event.source, 'user_id', None)
if not user_id:
    return  # 沒 user_id 就跳過處理


    # 嘗試取得使用者名稱
    try:
        if event.source.type == "group":
            profile = line_bot_api.get_group_member_profile(event.source.group_id, user_id)
        elif event.source.type == "room":
            profile = line_bot_api.get_room_member_profile(event.source.room_id, user_id)
        else:
            profile = line_bot_api.get_profile(user_id)
        display_name = profile.display_name
    except:
        display_name = "未知使用者"

    # 指令處理：統計
    if text == "次數":
        if not profanity_counter:
            reply = "目前沒有紀錄"
        else:
            lines = [f"{data['name']}: {data['count']} 次" for data in profanity_counter.values()]
            reply = "說髒話次數：\n" + "\n".join(lines)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    # 指令處理：排行榜
    if text == "沒水準":
        if not profanity_counter:
            reply = "目前沒有紀錄"
        else:
            top_user = max(profanity_counter.values(), key=lambda x: x["count"])
            reply = f"目前最沒水準的是：{top_user['name']}（{top_user['count']} 次）"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    # 偵測髒話：單字型（精確匹配）
    matched = False
    for word in word_profanities:
        if re.search(rf'\b{re.escape(word)}\b', text):
            matched = True
            break

    # 偵測髒話：片語型（模糊出現）
    if not matched:
        for phrase in phrase_profanities:
            if phrase in text:
                matched = True
                break

    if matched:
        if user_id not in profanity_counter:
            profanity_counter[user_id] = {"name": display_name, "count": 1}
        else:
            profanity_counter[user_id]["count"] += 1

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"{display_name} 不要說髒話！")
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
