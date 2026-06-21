import os
import anthropic
import requests
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
                "content": "あなたはThreadsのアフィリエイト投稿を作成するアシスタントです。以下の条件で投稿文を作成してください。\n\nテーマ：" + theme + "\nアフィリエイトURL：" + affiliate_url + "\n\n条件：\n- 500文字以内\n- 商品の魅力を自然に伝える\n- URLを末尾に含める\n- ハッシュタグを3つ含める\n- 押しつけがましくない自然な文章\n\n投稿文のみを出力してください。"
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

def main():
    posts = [
        {
            "theme": "ガジェット好きにおすすめの完全ワイヤレスイヤホン",
            "url": "https://もしもアフィリエイトのリンク"
        }
    ]

    for post in posts:
        print("投稿生成中：" + post["theme"])
        text = generate_post(post["theme"], post["url"])
        print("生成された投稿：\n" + text + "\n")
        result = create_threads_post(text)
        print("投稿結果：" + str(result))

if __name__ == "__main__":
    main()