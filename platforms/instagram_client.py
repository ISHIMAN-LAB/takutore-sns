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


def _check(r: requests.Response, context: str = "") -> dict:
    """200 系以外で response body 込みの例外を投げる. raise_for_status の代替."""
    if r.status_code >= 400:
        prefix = f"[{context}] " if context else ""
        raise RuntimeError(f"{prefix}HTTP {r.status_code} {r.reason}: {r.text}")
    return r.json()


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
    container_id = _check(create_resp, "IG container create")["id"]

    # Step 2: コンテナのステータスを確認 (FINISHEDまで待つ)
    for _ in range(10):
        status_resp = requests.get(
            f"{base}/{container_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=30,
        )
        status = _check(status_resp, "IG container status").get("status_code")
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
    media_id = _check(publish_resp, "IG publish")["id"]
    return f"https://instagram.com/p/{media_id}"


def _wait_finished(container_id: str, token: str) -> None:
    """コンテナが FINISHED になるまで待つ（IG carousel の子/親で共用）。"""
    base = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
    for _ in range(20):
        r = requests.get(
            f"{base}/{container_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=30,
        )
        status = _check(r, "IG status").get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"IG container error: {r.json()}")
        time.sleep(3)
    raise RuntimeError(f"IG container {container_id} not FINISHED in time")


def post_carousel_to_instagram(caption: str, image_rels: list[str]) -> str:
    """カルーセル投稿（連載のタイトルカード＋本文コマ用）。
    image_rels はリポジトリ相対パス（images/serial/…）。IMAGE_BASE_URL から公開URLを組む。
    各画像で子コンテナ作成 → media_type=CAROUSEL の親 → publish。"""
    user_id = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]
    base_url = os.environ["IMAGE_BASE_URL"].rstrip("/")
    base = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

    children = []
    for rel in image_rels:
        r = requests.post(
            f"{base}/{user_id}/media",
            data={
                "image_url": f"{base_url}/{rel}",
                "is_carousel_item": "true",
                "access_token": token,
            },
            timeout=60,
        )
        cid = _check(r, "IG child create")["id"]
        _wait_finished(cid, token)
        children.append(cid)

    r = requests.post(
        f"{base}/{user_id}/media",
        data={
            "media_type": "CAROUSEL",
            "children": ",".join(children),
            "caption": caption,
            "access_token": token,
        },
        timeout=60,
    )
    parent_id = _check(r, "IG carousel create")["id"]
    _wait_finished(parent_id, token)

    r = requests.post(
        f"{base}/{user_id}/media_publish",
        data={"creation_id": parent_id, "access_token": token},
        timeout=30,
    )
    media_id = _check(r, "IG publish")["id"]
    return f"https://instagram.com/p/{media_id}"
