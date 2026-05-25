"""
X (Twitter) API クライアント
2026年2月以降のpay-per-use対応(投稿1件 約$0.01)

必要な環境変数:
  X_API_KEY            (Consumer Key)
  X_API_SECRET         (Consumer Secret)
  X_ACCESS_TOKEN
  X_ACCESS_TOKEN_SECRET

セットアップ手順:
  1. https://developer.x.com/ で開発者アカウント作成
  2. プロジェクト&アプリ作成 → Read and Write 権限
  3. 上記の4つのキー/シークレットを発行
  4. GitHub Actions Secrets に登録
"""
import os
import tweepy


def _get_client():
    return tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )


def _get_v1_api():
    """画像アップロードはv1.1が必要"""
    auth = tweepy.OAuth1UserHandler(
        os.environ["X_API_KEY"],
        os.environ["X_API_SECRET"],
        os.environ["X_ACCESS_TOKEN"],
        os.environ["X_ACCESS_TOKEN_SECRET"],
    )
    return tweepy.API(auth)


def post_to_x(text: str, image_path: str | None = None) -> str:
    client = _get_client()
    media_ids = None

    if image_path:
        api_v1 = _get_v1_api()
        media = api_v1.media_upload(image_path)
        media_ids = [media.media_id]

    response = client.create_tweet(text=text, media_ids=media_ids)
    tweet_id = response.data["id"]
    return f"https://x.com/i/status/{tweet_id}"
