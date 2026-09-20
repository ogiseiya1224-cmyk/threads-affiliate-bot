import os
import base64
import requests
import nacl.public
import nacl.encoding

THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
THREADS_APP_SECRET = os.getenv("THREADS_APP_SECRET")
GH_PAT = os.getenv("GH_PAT")
GH_REPO = os.getenv("GH_REPO")

def refresh_token():
    url = "https://graph.threads.net/refresh_access_token"
    params = {
        "grant_type": "th_refresh_token",
        "access_token": THREADS_ACCESS_TOKEN
    }
    res = requests.get(url, params=params)
    data = res.json()

    if "access_token" not in data:
        print("リフレッシュ失敗: " + str(data))
        return None

    new_token = data["access_token"]
    print("リフレッシュ成功")
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

if __name__ == "__main__":
    new_token = refresh_token()
    if new_token:
        update_github_secret(new_token)