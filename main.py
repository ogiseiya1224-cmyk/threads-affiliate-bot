import os
import random
import csv
import json
import base64
import anthropic
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

THREADS_USER_ID = os.getenv("THREADS_USER_ID")
THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
THREADS_APP_SECRET = os.getenv("THREADS_APP_SECRET")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GH_PAT = os.getenv("GH_PAT")
GH_REPO = os.getenv("GH_REPO")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def refresh_token():
    url = "https://graph.threads.net/refresh_access_token"
    params = {
        "grant_type": "th_refresh_token",
        "access_token": THREADS_ACCESS_TOKEN
    }
    res = requests.get(url, params=params)
    data = res.json()

    if "access_token" not in data:
        print("トークンリフレッシュ失敗: " + str(data))
        return None

    new_token = data["access_token"]
    print("トークンリフレッシュ成功")

    # GitHub Secretsを更新
    if GH_PAT and GH_REPO:
        update_github_secret(new_token)

    return new_token

def update_github_secret(new_token):
    headers = {
        "Authorization": "token " + GH_PAT,
        "Accept": "application/vnd.github.v3+json"
    }
    key_res = requests.get(
        "https://api.github.com/repos/" + GH_REPO + "/actions/secrets/public-key",
        headers=headers
    )
    key_data = key_res.json()
    key_id = key_data["key_id"]
    public_key = key_data["key"]

    import nacl.public
    import nacl.encoding

    pk = nacl.public.PublicKey(public_key, nacl.encoding.Base64Encoder)
    sealed_box = nacl.public.SealedBox(pk)
    encrypted = sealed_box.encrypt(new_token.encode())
    encrypted_value = base64.b64encode(encrypted).decode()

    update_res = requests.put(
        "https://api.github.com/repos/" + GH_REPO + "/actions/secrets/THREADS_ACCESS_TOKEN",
        headers=headers,
        json={"encrypted_value": encrypted_value, "key_id": key_id}
    )
    if update_res.status_code in [201, 204]:
        print("GitHub Secrets更新成功")
    else:
        print("GitHub Secrets更新失敗: " + str(update_res.json()))

    # トークンを暗号化
    import nacl.public
    import nacl.encoding

    pk = nacl.public.PublicKey(public_key, nacl.encoding.Base64Encoder)
    sealed_box = nacl.public.SealedBox(pk)
    encrypted = sealed_box.encrypt(new_token.encode())
    encrypted_value = base64.b64encode(encrypted).decode()

    # Secretsを更新
    update_res = requests.put(
        "https://api.github.com/repos/" + GH_REPO + "/actions/secrets/THREADS_ACCESS_TOKEN",
        headers=headers,
        json={"encrypted_value": encrypted_value, "key_id": key_id}
    )
    if update_res.status_code in [201, 204]:
        print("GitHub Secrets更新成功")
    else:
        print("GitHub Secrets更新失敗: " + str(update_res.json()))

def get_ogp_image(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(res.text, "lxml")
        
        # OGP画像を試す
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            return og_image["content"]
        
        # Amazon商品画像を試す
        img = soup.find("img", {"id": "landingImage"})
        if img:
            src = img.get("src") or img.get("data-src")
            if src and src.startswith("http"):
                return src
        
        return None
    except:
        return None

def generate_post(theme, affiliate_url):
    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": "あなたはThreadsのアフィリエイト投稿を作成するプロのコピーライターです。以下の条件で投稿文を作成してください。\n\nテーマ：" + theme + "\nアフィリエイトURL：" + affiliate_url + "\n\n条件：\n- 500文字以内\n- 冒頭の1〜2文で思わず続きを読みたくなる導入を作る（感嘆・驚き・共感・問いかけなどを自然に使う）\n- 一部にあえて曖昧な表現や謎めいた言い回しを使い「どういうこと？」と読者に疑問を持たせる\n- 商品の魅力を押しつけがましくなく自然に伝える\n- URLを末尾に含める\n- ハッシュタグを3つ含める\n- 人が書いたような自然な文体\n\n投稿文のみを出力してください。"
            }
        ]
    )
    return message.content[0].text

def create_threads_post(text, image_url=None):
    container_url = "https://graph.threads.net/v1.0/" + THREADS_USER_ID + "/threads"
    
    if image_url:
        container_params = {
            "media_type": "IMAGE",
            "image_url": image_url,
            "text": text,
            "access_token": THREADS_ACCESS_TOKEN
        }
    else:
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
    # トークンを毎回リフレッシュ
    # refresh_token()

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
         {
            "theme": "ケーブルが絡まるストレスから解放、巻き取り式が便利すぎる",
            "url": "http://msm.to/EyRzCSv"
        },
        {
            "theme": "持ち運びに最適、どこでも快適に使えるコンパクトマウス",
            "url": "http://msm.to/EpeXrgV"
        },
         {
            "theme": "デスクが一気にスッキリ、絡みにくい形状記憶ケーブルが便利",
            "url": "http://msm.to/LiwWBQ"
        },
        {
            "theme": "充電器とモバイルバッテリーがこれ1台、旅行にも最強すぎる",
            "url": "http://msm.to/3k22rBO"
        },
        {
            "theme": "乗るだけで体の状態をチェック、毎日の健康管理が楽しくなる体重計",
            "url": "http://msm.to/2RV6nn"
        },
        {
            "theme": "セルフカット派にもおすすめ、プロ仕様の切れ味がすごいバリカン",
            "url": "http://msm.to/AqUOjq2"
        },
         {
            "theme": "歯磨きが面倒な人ほど使ってほしい、電動歯ブラシの快適さ",
            "url": "http://msm.to/GASNxP7"
        },
         {
            "theme": "毎日の健康管理に、家で簡単に測れる上腕式血圧計",
            "url": "http://msm.to/8BNmFfC"
        },
         {
            "theme": "家で手軽に全身ケア、振動するフォームローラーが気持ちいい",
            "url": "http://msm.to/DlGbx21"
        },
         {
            "theme": "旅行やアウトドアの思い出を残すなら、小さくても本格的なアクションカメラ",
            "url": "https://link.amazon/B0fJPTh1g"
        },
        {
            "theme": "スマホ動画が一気にプロっぽくなる、手ブレを抑えるスマホジンバル",
            "url": "https://link.amazon/B08sCxyb7"
        },
        {
            "theme": "家でも旅行先でも映画館に、持ち運べるプロジェクターが最高",
            "url": "https://link.amazon/B0djnjJYa"
        },
        {
            "theme": "デスクをスッキリさせたい人へ、コンパクトなのに打ちやすいキーボード",
            "url": "https://link.amazon/B04NFfHTB"
        },
        {
            "theme": "モニター周りが一気に快適に、デスク環境を整えるならこれ",
            "url": "https://link.amazon/B0fXjiy8q"
        },
        {
            "theme": "デスクの手元だけ明るくしたいなら、モニター上のライトが便利",
            "url": "https://link.amazon/B0fBraZwI"
        },
         {
            "theme": "掃除する時間を減らしたい人へ、コンパクトなロボット掃除機",
            "url": "https://link.amazon/B06Y1wg7h"
        },
         {
            "theme": "スマホや小物をサッと持ち歩ける、身軽に出かけたい人の便利バッグ",
            "url": "https://link.amazon/B0be31fuY"
        },
         {
            "theme": "耳をふさがない開放感、イヤーカフ型イヤホンが新感覚すぎる",
            "url": "https://link.amazon/B0hXuriWl"
        },
         {
            "theme": "ノートPCまで充電できる、165Wの超パワフルなモバイルバッテリー",
            "url": "https://link.amazon/B0g4VxdcM"
        },
    ]

    post = random.choice(posts)
    print("投稿生成中：" + post["theme"])
    text = generate_post(post["theme"], post["url"])
    print("生成された投稿：\n" + text + "\n")
    
    image_url = get_ogp_image(post["url"])
    if image_url:
        print("画像取得成功：" + image_url)
    else:
        print("画像取得失敗、テキスト投稿に切り替え")
    
    result = create_threads_post(text, image_url)
    print("投稿結果：" + str(result))

    if "id" in result:
        post_id = result["id"]
        engagement = get_engagement(post_id)
        save_to_csv(post["theme"], post_id, engagement)
        print("エンゲージメント：" + str(engagement))

if __name__ == "__main__":
    main()