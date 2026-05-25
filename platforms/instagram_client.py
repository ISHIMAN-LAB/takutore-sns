"""
Instagram Business投稿クライアント (Meta Graph API)

Instagramは画像必須。テキストのみ投稿不可。
画像はパブリックURLからアップロードする必要があるため、
GitHub raw URL or Cloudinary or S3 などを使う。

必要な環境変数:
  IG_USER_ID           (Instagram Business Account ID)
  IG_ACCESS_TOKEN      (FBページトークンと同じものでOK)
  IMAGE_BASE_URL       (画像のホストベースURL。例: https://raw.githubusercontent.com/USER/REPO/main/)

セットアップ:
  1. Instagramアカウントを「ビジネス」または「クリエイター」に切り替え
  2. Facebookページに連携(必須)
  3. Meta Developer App の Instagram Graph API で権限取得:
     instagram_basic, instagram_content_publish, pages_read_engagement
"""
import os
import time
import requests

GRAPH_API_VERSION = "v21.0"


def post_to_instagram(caption: str, image_path: str) -> str:
    user_id = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]
    base_url = os.environ["IMAGE_BASE_URL"].rstrip("/")

    # 画像はrepo内のパスから公開URLを組み立てる
    # 例: images/01-24h-deep-night.jpg → {IMAGE_BASE_URL}/images/01-24h-deep-night.jpg
    if image_path.startswith("/"):
        # 絶対パス → リポジトリルートからの相対パスに変換が必要
        # ここでは末尾の "images/xxx.jpg" 部分を取り出す
        rel = image_path.split("takutore-sns/")[-1] if "takutore-sns/" in image_path else os.path.basename(image_path)
    else:
        rel = image_path
    image_url = f"{base_url}/{rel}"

    base = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

    # Step 1: メディアコンテナ作成
    create_url = f"{base}/{user_id}/media"
    create_resp = requests.post(
        create_url,
        data={
            "image_url": image_url,
            "caption": caption,
            "access_token": token,
        },
        timeout=60,
    )
    create_resp.raise_for_status()
    container_id = create_resp.json()["id"]

    # Step 2: コンテナのステータスを確認 (FINISHEDまで待つ)
    for _ in range(10):
        status_resp = requests.get(
            f"{base}/{container_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=30,
        )
        status_resp.raise_for_status()
        status = status_resp.json().get("status_code")
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise RuntimeError(f"IG container error: {status_resp.json()}")
        time.sleep(3)

    # Step 3: 公開
    publish_url = f"{base}/{user_id}/media_publish"
    publish_resp = requests.post(
        publish_url,
        data={"creation_id": container_id, "access_token": token},
        timeout=30,
    )
    publish_resp.raise_for_status()
    media_id = publish_resp.json()["id"]
    return f"https://instagram.com/p/{media_id}"
