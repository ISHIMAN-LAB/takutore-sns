#!/usr/bin/env python3
"""卓トレ高田馬場 Instagram 単発投稿テストスクリプト.

Usage:
    # ドライラン (デフォルト): メディアコンテナ作成までで停止、実投稿はしない
    python3 post_ig.py \\
        --image-url https://picsum.photos/1080/1080 \\
        --caption "テスト投稿 #卓トレ #高田馬場"

    # 実投稿
    python3 post_ig.py \\
        --image-url https://example.com/foo.jpg \\
        --caption "本番投稿" \\
        --no-dry-run

`.env` から IG_USER_ID / IG_ACCESS_TOKEN を読みます。
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

GRAPH = "https://graph.facebook.com/v21.0"
SCRIPT_DIR = Path(__file__).resolve().parent
ENV_PATH = SCRIPT_DIR / ".env"
REFRESH_SCRIPT = SCRIPT_DIR / "refresh_token.py"


def load_env(path):
    env = {}
    if not path.exists():
        sys.exit(f"ERROR: {path} が見つかりません。先にトークン取得を済ませてください。")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def http(method, url, data=None):
    if data is not None:
        body = urlencode(data).encode()
        req = Request(url, data=body, method=method)
    else:
        req = Request(url, method=method)
    try:
        with urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        body = e.read().decode(errors="replace")
        sys.exit(f"HTTP {e.code} {e.reason}\n{body}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--image-url", required=True, help="公開アクセス可能な画像URL (HTTPS)")
    parser.add_argument("--caption", required=True, help="投稿キャプション (ハッシュタグ含む)")
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="True ならコンテナ作成までで停止 (デフォルト). 実投稿には --no-dry-run",
    )
    args = parser.parse_args()

    # 投稿前に長期トークンの残日数を確認し、閾値未満なら自動更新
    if REFRESH_SCRIPT.exists():
        result = subprocess.run(
            [sys.executable, str(REFRESH_SCRIPT)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"WARNING: トークン更新失敗 (続行します): {result.stderr.strip()}", file=sys.stderr)
        elif result.stdout.startswith("REFRESHED"):
            print(f"[Token] {result.stdout.strip()}")
        # SKIPPED の場合はあえて出さない (ログ過多防止)

    env = load_env(ENV_PATH)
    try:
        ig_user_id = env["IG_USER_ID"]
        token = env["IG_ACCESS_TOKEN"]
    except KeyError as e:
        sys.exit(f"ERROR: .env に {e.args[0]} がありません")

    print(f"Target IG user: {ig_user_id}")
    print(f"Image URL:      {args.image_url}")
    print(f"Caption:        {args.caption}")
    print(f"Mode:           {'DRY RUN' if args.dry_run else 'LIVE POST'}")
    print()

    # Step 1: メディアコンテナ作成
    print("[Step 1/3] メディアコンテナ作成 ...")
    r = http(
        "POST",
        f"{GRAPH}/{ig_user_id}/media",
        {"image_url": args.image_url, "caption": args.caption, "access_token": token},
    )
    container_id = r["id"]
    print(f"  container_id: {container_id}")

    if args.dry_run:
        print("\nDRY RUN: ここで停止します (ポーリング・公開はスキップ).")
        print("コンテナは Instagram 側で未公開のまま残り、24時間で自動失効します.")
        print("実投稿するには --no-dry-run を付けて再実行してください.")
        return

    # Step 2: ステータスポーリング
    print("\n[Step 2/3] コンテナ ready 待ち (最大 30 秒) ...")
    status = None
    for i in range(10):
        r = http(
            "GET",
            f"{GRAPH}/{container_id}?{urlencode({'fields': 'status_code', 'access_token': token})}",
        )
        status = r.get("status_code")
        print(f"  [{i+1}/10] status={status}")
        if status == "FINISHED":
            break
        if status == "ERROR":
            sys.exit(f"ERROR: container {container_id} failed: {r}")
        time.sleep(3)
    else:
        sys.exit(f"ERROR: container {container_id} not ready after 30s (last status: {status})")

    # Step 3: 公開
    print("\n[Step 3/3] 公開 ...")
    r = http(
        "POST",
        f"{GRAPH}/{ig_user_id}/media_publish",
        {"creation_id": container_id, "access_token": token},
    )
    media_id = r["id"]
    print(f"  media_id: {media_id}")

    # permalink 取得
    try:
        r = http(
            "GET",
            f"{GRAPH}/{media_id}?{urlencode({'fields': 'permalink', 'access_token': token})}",
        )
        permalink = r.get("permalink", f"https://instagram.com/p/{media_id}")
    except SystemExit:
        permalink = f"(permalink取得失敗) media_id={media_id}"

    print(f"\nDONE. {permalink}")


if __name__ == "__main__":
    main()
