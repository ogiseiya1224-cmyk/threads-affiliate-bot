import os
import random
import csv
import anthropic
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

THREADS_USER_ID = os.getenv("THREADS_USER_ID")
THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def generate_post(theme, affiliate_url):
    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": "あなたはThreadsのアフィリエイト投稿を作成するプロのコピーライターです。以下の条件で投稿文を作成してください。\n\nテーマ：" + theme + "\nアフィリエイトURL：" + affiliate_url + "\n\n条件：\n- 200文字以内\n- 冒頭の1〜2文で思わず続きを読みたくなる導入を作る（感嘆・驚き・共感・問いかけ・倒置法などを自然に使う）\n- 商品の魅力を自然に伝える\n- 一部にあえて曖昧な表現や謎めいた言い回しを使い「どういうこと？」と読者に疑問を持たせる\n- URLを末尾に含める\n- ハッシュタグを3つ含める\n- 押しつけがましくない自然な文章\n\n投稿文のみを出力してください。"
            }
        ]
    )
    return message.content[0].text

def create_threads_post(text):
    container_url = "https://graph.threads.net/v1.0/" + THREADS_USER_ID + "/threads"
    container_params = {
        "media_type": "TEXT",
        "text": text,
        "access_token": THREADS_ACCESS_TOKEN
    }
    container_res = requests.post(container_url, params=container_params)
    container_data = container_res.json()

    if "id" not in container_data:
        raise Exception("コンテナ作成失敗: " + str(container_data))

    container_id = container_data["id"]

    publish_url = "https://graph.threads.net/v1.0/" + THREADS_USER_ID + "/threads_publish"
    publish_params = {
        "creation_id": container_id,
        "access_token": THREADS_ACCESS_TOKEN
    }
    publish_res = requests.post(publish_url, params=publish_params)
    return publish_res.json()

def get_engagement(post_id):
    url = "https://graph.threads.net/v1.0/" + post_id + "/insights"
    params = {
        "metric": "likes,reposts,replies,views",
        "access_token": THREADS_ACCESS_TOKEN
    }
    res = requests.get(url, params=params)
    data = res.json()

    engagement = {"likes": 0, "reposts": 0, "replies": 0, "views": 0}
    if "data" in data:
        for item in data["data"]:
            name = item.get("name")
            value = item.get("values", [{}])[0].get("value", 0)
            if name in engagement:
                engagement[name] = value
    return engagement

def save_to_csv(theme, post_id, engagement):
    filename = "engagement_log.csv"
    file_exists = os.path.exists(filename)
    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["date", "theme", "post_id", "likes", "reposts", "replies", "views"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            theme,
            post_id,
            engagement["likes"],
            engagement["reposts"],
            engagement["replies"],
            engagement["views"]
        ])

def main():
    posts = [
        {
            "theme": "完全ワイヤレスイヤホン（Technics EAH-AZ100またはBose QC Ultra）",
            "url": "https://link.amazon/B0iw3Ui4w"
        },
        {
            "theme": "SwitchBot ハブ3でスマートホームを始めよう",
            "url": "https://link.amazon/B01y627WE"
        },
        {
            "theme": "Anker 65Wモバイルバッテリーで充電の不安をゼロに",
            "url": "https://link.amazon/B001mPj5V"
        },
        {
            "theme": "SwitchBot CO2センサーで室内環境を見える化しよう",
            "url": "https://link.amazon/B09v8E73s"
        },
        {
            "theme": "USB急速充電器（多ポート）で充電環境をスッキリさせよう",
            "url": "https://link.amazon/B0eE7ReM5"
        },
        {
            "theme": "Amazon Fire TV Stick HDでテレビをスマート化しよう",
            "url": "https://link.amazon/B04DAlieM"
        },
        {
            "theme": "Ulike脱毛器Air 10 Maxで自宅脱毛を始めよう",
            "url": "https://link.amazon/B0cy6mLnP"
        },
        {
            "theme": "ARグラスXREAL Oneで新しい映像体験を",
            "url": "https://link.amazon/B0ibVWQ20"
        },
        {
            "theme": "冷却プレート付きハンディファンで夏を快適に",
            "url": "https://link.amazon/B07v9cC0G"
        },
        {
            "theme": "レーザー・EMS美顔器で自宅エステを始めよう",
            "url": "https://link.amazon/B0brA7kaB"
        },
        {
            "theme": "スマホもタブレットも急速充電、手のひらサイズの充電器が優秀すぎた",
            "url": "http://msm.to/4oTxvpG"
        },
    ]

    post = random.choice(posts)
    print("投稿生成中：" + post["theme"])
    text = generate_post(post["theme"], post["url"])
    print("生成された投稿：\n" + text + "\n")
    result = create_threads_post(text)
    print("投稿結果：" + str(result))

    if "id" in result:
        post_id = result["id"]
        engagement = get_engagement(post_id)
        save_to_csv(post["theme"], post_id, engagement)
        print("エンゲージメント：" + str(engagement))

if __name__ == "__main__":
    main()