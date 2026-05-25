"""
卓トレ高田馬場店 SNS自動投稿
- posts.json から「最近使ってない投稿」を選ぶ
- 各プラットフォームへ投稿
- state.json で使用履歴を管理
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from platforms.x_client import post_to_x
from platforms.facebook_client import post_to_facebook
from platforms.instagram_client import post_to_instagram

ROOT = Path(__file__).parent
POSTS_FILE = ROOT / "posts.json"
STATE_FILE = ROOT / "state.json"

# どのプラットフォームを有効にするか (env varで制御も可能)
ENABLED_PLATFORMS = {
    "x": os.getenv("ENABLE_X", "true").lower() == "true",
    "facebook": os.getenv("ENABLE_FB", "true").lower() == "true",
    "instagram": os.getenv("ENABLE_IG", "true").lower() == "true",
}

# ドライラン(投稿せずログだけ)
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"


def load_posts():
    with POSTS_FILE.open(encoding="utf-8") as f:
        data = json.load(f)
    return [p for p in data["posts"] if p.get("enabled", True)]


def load_state():
    if not STATE_FILE.exists():
        return {"history": {}}
    with STATE_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def pick_next_post(posts, state):
    """最後に使った日が古い順 → 一度も使ってないやつ優先"""
    history = state.get("history", {})

    def last_used(post_id):
        return history.get(post_id, "1970-01-01")

    sorted_posts = sorted(posts, key=lambda p: last_used(p["id"]))
    return sorted_posts[0]


def main():
    posts = load_posts()
    state = load_state()
    post = pick_next_post(posts, state)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"[{today}] Selected: {post['id']} — {post['theme']}")

    image_path = ROOT / post["image_file"]
    image_exists = image_path.exists()

    results = {}

    if ENABLED_PLATFORMS["x"]:
        try:
            if DRY_RUN:
                print(f"[DRY] X: {post['x_text'][:50]}...")
                results["x"] = "DRY"
            else:
                results["x"] = post_to_x(
                    text=post["x_text"],
                    image_path=str(image_path) if image_exists else None,
                )
        except Exception as e:
            print(f"X error: {e}", file=sys.stderr)
            results["x"] = f"ERROR: {e}"

    if ENABLED_PLATFORMS["facebook"]:
        try:
            if DRY_RUN:
                print(f"[DRY] FB: {post['long_caption'][:50]}...")
                results["facebook"] = "DRY"
            else:
                results["facebook"] = post_to_facebook(
                    caption=post["long_caption"],
                    image_path=str(image_path) if image_exists else None,
                )
        except Exception as e:
            print(f"FB error: {e}", file=sys.stderr)
            results["facebook"] = f"ERROR: {e}"

    if ENABLED_PLATFORMS["instagram"]:
        if not image_exists:
            print(f"IG skipped: {post['image_file']} not found (IG requires image)")
            results["instagram"] = "SKIPPED: no image"
        else:
            try:
                if DRY_RUN:
                    print(f"[DRY] IG: {post['long_caption'][:50]}...")
                    results["instagram"] = "DRY"
                else:
                    results["instagram"] = post_to_instagram(
                        caption=post["long_caption"],
                        image_path=str(image_path),
                    )
            except Exception as e:
                print(f"IG error: {e}", file=sys.stderr)
                results["instagram"] = f"ERROR: {e}"

    # 履歴更新 (どこか1つでも成功してたら記録)
    if any("ERROR" not in str(v) and v != "SKIPPED: no image" for v in results.values()):
        state.setdefault("history", {})[post["id"]] = today
        save_state(state)

    print(f"Results: {results}")
    return results


if __name__ == "__main__":
    main()
