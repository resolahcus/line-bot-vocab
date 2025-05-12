from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage, MemberJoinedEvent
from linebot.exceptions import InvalidSignatureError
import os
import re
import random

app = Flask(__name__)

bulls_and_cows_game = {}

line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))

# 單字型髒話（需精準比對）
word_profanities = ["幹", "操", "糙"]

# 片語型髒話（只要出現就算）
phrase_profanities = [
    "靠北", "靠杯", "靠邀", "靠腰", "幹你娘", "你媽", "他媽", "操你媽", "三小", "啥小",
    "去你的", "去你媽", "擊敗", "雞掰", "智障", "白癡", "傻逼", "低能", "低能兒", "破麻",
    "破病", "肏", "狗幹", "去死", "耖", "Fuck", "fuck", "Shit", "shit"
]

# 髒話次數紀錄
profanity_counter = {}

# 籤文內容
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
    "世紀大衰鬼": 0.5
}

# 成就系統定義
achievements_definitions = [
    ("素質低落", lambda data: data.get("count", 0) >= 5),
    ("懺悔使者", lambda data: data.get("forgive_count", 0) >= 3),
    ("洗刷冤屈", lambda data: data.get("wash_count", 0) >= 1),
    ("善言守護者", lambda data: data.get("wash_count", 0) >= 3),
]

def check_achievements(user_id):
    user_data = profanity_counter[user_id]
    unlocked = []
    if "achievements" not in user_data:
        user_data["achievements"] = set()

    for name, condition in achievements_definitions:
        if name not in user_data["achievements"] and condition(user_data):
            user_data["achievements"].add(name)
            unlocked.append(name)

    return unlocked

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

@handler.add(MemberJoinedEvent)
def handle_member_joined(event):
    group_id = event.source.group_id


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    user_id = getattr(event.source, 'user_id', None)
    if not user_id:
        return
        
    group_key = getattr(event.source, 'group_id', None) or getattr(event.source, 'room_id', None) or user_id
    
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

    if user_id not in profanity_counter:
        profanity_counter[user_id] = {"name": display_name, "count": 0, "wash_count": 0, "forgive_count": 0, "achievements": set()}

    if text in ["稱號", "成就"]:
        achs = profanity_counter[user_id].get("achievements", set())
        if not achs:
            reply = f"{display_name} 還沒有獲得任何稱號喔！"
        else:
            reply = f"{display_name} 目前擁有稱號：\n" + "\n".join(f"🏅 {a}" for a in achs)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    if "mission" in profanity_counter[user_id]:
        mission_text = profanity_counter[user_id]["mission"]
        match = re.search(r"[「『](.*?)[」』]", mission_text)
        if match:
            expected_phrase = match.group(1)
        else:
            expected_phrase = re.sub(r"請輸入|就能洗白！|完成後.*", "", mission_text).strip()

        if expected_phrase and expected_phrase in text:
            profanity_counter[user_id]["count"] = max(0, profanity_counter[user_id]["count"] - 1)
            profanity_counter[user_id]["wash_count"] = profanity_counter[user_id].get("wash_count", 0) + 1
            del profanity_counter[user_id]["mission"]
            reply = f"{display_name} 洗白成功！髒話次數已減一"
            unlocked = check_achievements(user_id)
            if unlocked:
                reply += "\n🎉 解鎖成就：" + "、".join(unlocked)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
            return
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="你還沒完成洗白任務喔～快照著做！"))
            return

    forgive_words = ["我錯了", "抱歉", "對不起", "原諒我"]
    if any(word in text for word in forgive_words):
        profanity_counter[user_id]["forgive_count"] = profanity_counter[user_id].get("forgive_count", 0) + 1
        response_list = [
            f"{display_name} 這次就原諒你吧 ",
            f"{display_name} 好好重新做人！",
            f"{display_name} 好啦，原諒你一次"
        ]
        reply = random.choice(response_list)
        unlocked = check_achievements(user_id)
        if unlocked:
            reply += "\n🎉 解鎖成就：" + "、".join(unlocked)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    if text == "次數":
        if not profanity_counter:
            reply = "目前沒有紀錄"
        else:
            lines = [f"{data['name']}: {data['count']} 次" for data in profanity_counter.values()]
            reply = "說髒話次數：\n" + "\n".join(lines)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    if text == "沒水準":
        if not profanity_counter:
            reply = "目前沒有紀錄"
        else:
            top_user = max(profanity_counter.values(), key=lambda x: x["count"])
            reply = f"目前最沒水準的是：{top_user['name']}（{top_user['count']} 次）"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    if text == "洗白":
        cleansing_missions = [
            "請輸入『我愛這個群組，我錯了』",
            "誠心三連發：對不起對不起對不起",
            "請輸入『請原諒我，我會做個乾淨的人』",
            "請說出悔意：『髒話無益，口出善言』",
            "輸入『我不再說壞話了』就能洗白！"
        ]
        selected_mission = random.choice(cleansing_missions)
        profanity_counter[user_id]["mission"] = selected_mission
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"{display_name}，你的洗白任務來了：\n{selected_mission}\n完成後我會幫你減少一次髒話紀錄喔 ")
        )
        return

    matched = any(re.search(rf'\b{re.escape(word)}\b', text) for word in word_profanities) or \
              any(phrase in text for phrase in phrase_profanities)

    if matched:
        profanity_counter[user_id]["count"] += 1
        reply = f"{display_name} 不要說髒話！"
        unlocked = check_achievements(user_id)
        if unlocked:
            reply += "\n🎉 解鎖成就：" + "、".join(unlocked)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

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

 # 猜數字：開始遊戲
    if text == "猜數字":
        if group_key in bulls_and_cows_game:
            reply_text = "目前已有猜數字遊戲進行中，請先完成或輸入『結束遊戲』結束現有遊戲。"
        else:
            digits = random.sample("0123456789", 4)
            answer = ''.join(digits)
            bulls_and_cows_game[group_key] = {
                "answer": answer,
                "tries": 0,
                "starter": user_id  # 記錄發起者
            }
            reply_text = f"{display_name} 開始了一場猜數字遊戲！\n請輸入 4 位不重複的數字來猜猜看！"
    
    # 放棄遊戲
    elif text in ["放棄", "結束遊戲"] and group_key in bulls_and_cows_game:
        game = bulls_and_cows_game[group_key]
        if game.get("starter") != user_id:
            reply_text = f"只有遊戲發起者（{game['starter']}）才能結束這場遊戲喔！"
        else:
            answer = game["answer"]
            reply_text = f"遊戲結束！答案是 {answer}"
            del bulls_and_cows_game[group_key]

    
    # 進行遊戲中
    elif group_key in bulls_and_cows_game:
        if re.fullmatch(r"\d{4}", text) and len(set(text)) == 4:
            game = bulls_and_cows_game[group_key]
            answer = game["answer"]
            game["tries"] += 1
            guess = text
            A = sum(a == b for a, b in zip(answer, guess))
            B = sum(min(guess.count(d), answer.count(d)) for d in set(guess)) - A

            if A == 4:
                reply_text = f"{display_name} 猜對了！答案是 {answer}，共猜了 {game['tries']} 次！"
                del bulls_and_cows_game[group_key]
            else:
                reply_text = f"{A}A{B}B，繼續猜！"
    else:
        return  # 無效輸入，不回應
        
    if 'reply_text' in locals():
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
