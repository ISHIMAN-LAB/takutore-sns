"""
Facebook Page投稿クライアント (Meta Graph API)

必要な環境変数:
  FB_PAGE_ID
  FB_PAGE_ACCESS_TOKEN   (長期トークン推奨。60日有効化必須)

セットアップ:
  1. https://developers.facebook.com/ でアプリ作成
  2. 卓トレ用のFacebookページを管理者権限で用意
  3. Graph API Explorer で pages_manage_posts, pages_read_engagement 権限取得
  4. 短期トークン → 長期トークン → ページトークンに変換
     参考: https://developers.facebook.com/docs/facebook-login/guides/access-tokens
"""
import os
import requests

GRAPH_API_VERSION = "v21.0"


def post_to_facebook(caption: str, image_path: str | None = None) -> str:
    page_id = os.environ["FB_PAGE_ID"]
    token = os.environ["FB_PAGE_ACCESS_TOKEN"]
    base = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

    if image_path:
        # 画像付き投稿
        url = f"{base}/{page_id}/photos"
        with open(image_path, "rb") as f:
            files = {"source": f}
            data = {"caption": caption, "access_token": token}
            r = requests.post(url, data=data, files=files, timeout=60)
    else:
        # テキストのみ
        url = f"{base}/{page_id}/feed"
        data = {"message": caption, "access_token": token}
        r = requests.post(url, data=data, timeout=30)

    r.raise_for_status()
    result = r.json()
    post_id = result.get("post_id") or result.get("id")
    return f"https://facebook.com/{post_id}"
