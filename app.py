from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage, MemberJoinedEvent
from linebot.exceptions import InvalidSignatureError
import os
import re
import random

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))

# 單字型髒話：需精準比對（避免幹什麼被誤判）
word_profanities = ["幹", "操", "糙"]
# 片語型髒話：可直接判斷是否出現在句中
phrase_profanities = [
    "靠北", "靠杯", "靠邀", "靠腰", "幹你娘", "你媽", "他媽", "操你媽", "三小", "啥小",
    "去你的", "去你媽", "擊敗", "雞掰", "智障", "白癡", "傻逼", "低能", "低能兒", "破麻",
    "破病", "肏", "狗幹", "去死", "耖", "Fuck", "fuck", "Shit", "shit"
]

# 髒話次數記錄
profanity_counter = {}

# 籤文資料
lottery_results = {
    "人品大爆發": "太神啦，做什麼事都會成功，大膽嘗試。",
    "上上籤": "今天事事順利，無論做什麼都會有好結果，值得一試。",
    "上籤": "運氣較好，今天可以勇敢嘗試，但也要保持謹慎。",
    "中籤": "今天的運勢一般，不過依然能有小小收穫，保持努力。",
    "下籤": "今天會有一些挑戰，但不必過於擔心，保持耐心。",
    "下下籤": "今天的運勢較差，建議保持低調，謹慎行事。",
    "世紀大衰鬼": "今天還是別出門了，好好待在家裡窩著吧。"
}
lottery_weights = {
    "人品大爆發": 0.5,
    "上上籤": 1,
    "上籤": 2,
    "中籤": 3,
    "下籤": 2,
    "下下籤": 1,
    "世紀大衰鬼" : 0.5
}

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

# 加入群組的處理器
@handler.add(MemberJoinedEvent)
def handle_member_joined(event):
    group_id = event.source.group_id
    bot_ids = []

    for member in event.joined.members:
        try:
            profile = line_bot_api.get_group_member_profile(group_id, member.user_id)
            if member.user_id != event.source.user_id:
                bot_ids.append({
                    'user_id': member.user_id,
                    'display_name': profile.display_name
                })
                print(f"[DEBUG] 加入群組的 bot: {profile.display_name} ({member.user_id})")
        except Exception as e:
            print(f"[DEBUG] 無法取得加入者資料: {member.user_id}, 錯誤: {e}")

    if bot_ids:
        for bot in bot_ids:
            print(f"偵測到其他 bot 加入：{bot['display_name']} ({bot['user_id']})")
    else:
        print("[DEBUG] 沒有其他 bot 加入")

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    user_id = getattr(event.source, 'user_id', None)
    if not user_id:
        return

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

    # 如果有洗白任務，檢查是否完成
    if user_id in profanity_counter and "mission" in profanity_counter[user_id]:
        expected_phrase = profanity_counter[user_id]["mission"].replace("請輸入", "").replace("就能洗白！", "").strip("：").strip(" ")
    if expected_phrase in text:
        # 用戶完成洗白任務，減少髒話次數
        profanity_counter[user_id]["count"] = max(0, profanity_counter[user_id]["count"] - 1)
        del profanity_counter[user_id]["mission"]  # 任務完成就清掉
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"{display_name} 洗白成功！髒話次數已減一 ")
        )
        return

    # 如果不是洗白任務，才檢查原諒詞彙
    forgive_words = ["我錯了", "抱歉", "對不起", "原諒我"]
    if any(word in text for word in forgive_words):
    # 檢查是否有洗白任務未完成
    if user_id not in profanity_counter or "mission" in profanity_counter[user_id]:
        response_list = [
            f"{display_name} 這次就原諒你吧 ",
            f"{display_name} 好好重新做人！",
            f"{display_name} 好啦，原諒你一次"
        ]
        reply = random.choice(response_list)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return
        
    # 指令：統計
    if text == "次數":
        if not profanity_counter:
            reply = "目前沒有紀錄"
        else:
            lines = [f"{data['name']}: {data['count']} 次" for data in profanity_counter.values()]
            reply = "說髒話次數：\n" + "\n".join(lines)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    # 指令：排行榜
    if text == "沒水準":
        if not profanity_counter:
            reply = "目前沒有紀錄"
        else:
            top_user = max(profanity_counter.values(), key=lambda x: x["count"])
            reply = f"目前最沒水準的是：{top_user['name']}（{top_user['count']} 次）"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    # 使用者輸入「洗白」指令
    if text == "洗白":
        cleansing_missions = [
            "請輸入『我愛這個群組，我錯了』",
            "誠心三連發：對不起對不起對不起",
            "請輸入『請原諒我，我會做個乾淨的人』",
            "請說出悔意：『髒話無益，口出善言』",
            "輸入『我不再說壞話了』就能洗白！"
        ]
        selected_mission = random.choice(cleansing_missions)
        # 把用戶目前任務存下來
        if user_id not in profanity_counter:
            profanity_counter[user_id] = {"name": display_name, "count": 0, "mission": selected_mission}
        else:
            profanity_counter[user_id]["mission"] = selected_mission

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"{display_name}，你的洗白任務來了：\n{selected_mission}\n完成後我會幫你減少一次髒話紀錄喔 ")
        )
        return
        
    # 偵測髒話
    matched = False
    for word in word_profanities:
        if re.search(rf'\b{re.escape(word)}\b', text):
            matched = True
            break

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
        return


    # 抽籤功能
    if "抽籤" in text:
        result = random.choices(
            list(lottery_results.keys()),
            weights=list(lottery_weights.values()),
            k=1
        )[0]
        response_message = lottery_results[result]
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"你的籤是：{result}\n{response_message}")
        )
        return

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
