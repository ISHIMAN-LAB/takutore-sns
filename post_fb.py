#!/usr/bin/env python3
"""卓トレ高田馬場 Facebook ページ単発投稿テストスクリプト.

Usage:
    # ドライラン (デフォルト): 投稿せず内容だけ表示
    python3 post_fb.py --message "テスト投稿"
    python3 post_fb.py --message "テスト投稿" --image-url https://picsum.photos/1080/1080

    # 実投稿
    python3 post_fb.py --message "本文" --no-dry-run
    python3 post_fb.py --message "本文" --image-url https://... --no-dry-run

`.env` から FB_PAGE_ID / FB_PAGE_ACCESS_TOKEN を読みます。
画像URL指定時は /photos エンドポイント、無ければ /feed エンドポイントを使います.

FB ページトークンは永続 (expires_at=0) なので、自動更新スクリプトは不要.
ただしユーザートークン (IG_ACCESS_TOKEN) が失効するとページトークンも連動失効するため、
.env の IG_ACCESS_TOKEN を refresh_token.py で生かし続けること.
"""
import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

GRAPH = "https://graph.facebook.com/v21.0"
ENV_PATH = Path(__file__).resolve().parent / ".env"


def load_env(path):
    if not path.exists():
        sys.exit(f"ERROR: {path} がありません")
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def http_post(url, data):
    body = urlencode(data).encode()
    try:
        with urlopen(Request(url, data=body, method="POST"), timeout=30) as r:
            return json.loads(r.read().decode())
    except HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode(errors='replace')}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--message", required=True, help="投稿本文")
    parser.add_argument("--image-url", help="(任意) 公開アクセス可能な画像URL. 指定すれば /photos に投稿")
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="True なら投稿せず内容だけ表示 (デフォルト). 実投稿には --no-dry-run",
    )
    args = parser.parse_args()

    env = load_env(ENV_PATH)
    for k in ("FB_PAGE_ID", "FB_PAGE_ACCESS_TOKEN"):
        if k not in env:
            sys.exit(f"ERROR: .env に {k} がありません")
    page_id = env["FB_PAGE_ID"]
    token = env["FB_PAGE_ACCESS_TOKEN"]

    print(f"Page ID:   {page_id}")
    print(f"Message:   {args.message}")
    print(f"Image URL: {args.image_url or '(なし — テキストのみ投稿)'}")
    print(f"Mode:      {'DRY RUN' if args.dry_run else 'LIVE POST'}")
    print()

    if args.dry_run:
        print("DRY RUN: 投稿しません. 実投稿には --no-dry-run を付けて再実行.")
        return

    if args.image_url:
        # 画像付き: /photos エンドポイント (画像URLを渡せる)
        r = http_post(f"{GRAPH}/{page_id}/photos", {
            "url": args.image_url,
            "caption": args.message,
            "access_token": token,
        })
        post_id = r.get("post_id") or r.get("id")
    else:
        # テキストのみ: /feed エンドポイント
        r = http_post(f"{GRAPH}/{page_id}/feed", {
            "message": args.message,
            "access_token": token,
        })
        post_id = r.get("id")

    if not post_id:
        sys.exit(f"ERROR: post_id が応答に無い: {r}")
    print(f"DONE. https://facebook.com/{post_id}")


if __name__ == "__main__":
    main()
