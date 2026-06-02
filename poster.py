"""
卓トレ高田馬場店 SNS自動投稿
- posts.json から「最近使ってない投稿」を選ぶ (条件を満たすもの)
- 各プラットフォームへ投稿
- state.json で使用履歴を管理

posts.json の各エントリで `condition` フィールドを指定すると条件付き投稿になる.
対応条件:
  - "rain_in_tokyo": 東京(高田馬場)が現在雨の時のみ投稿可
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

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


def is_raining_in_tokyo() -> bool:
    """Open-Meteo で高田馬場の現在天気を取得し、雨かどうか判定する.

    判定基準:
      - 降水量 0.5mm 以上 OR
      - WMO weather code が雨系 (51-67=雨, 80-82=しゅう雨, 95/96/99=雷雨)
    失敗時は False (= 雨と判定できない = 雨投稿はスキップ).
    """
    url = "https://api.open-meteo.com/v1/forecast?" + urlencode({
        "latitude": 35.7126,   # 高田馬場
        "longitude": 139.7038,
        "current": "weather_code,precipitation",
        "timezone": "Asia/Tokyo",
    })
    try:
        with urlopen(Request(url), timeout=10) as r:
            data = json.loads(r.read().decode()).get("current", {})
    except Exception as e:
        print(f"[weather] API failed: {e}", file=sys.stderr)
        return False
    code = data.get("weather_code", 0)
    precip = data.get("precipitation", 0) or 0
    is_rain_code = (51 <= code <= 67) or (80 <= code <= 82) or code in (95, 96, 99)
    is_rain = precip >= 0.5 or is_rain_code
    print(f"[weather] code={code} precip={precip}mm -> {'RAIN' if is_rain else 'no rain'}")
    return is_rain


# 条件 → 判定関数
CONDITION_HANDLERS = {
    "rain_in_tokyo": is_raining_in_tokyo,
}


def is_eligible(post) -> bool:
    """post.condition を満たしているか判定. 条件無しは常に True."""
    cond = post.get("condition")
    if not cond:
        return True
    handler = CONDITION_HANDLERS.get(cond)
    if handler is None:
        print(f"[warn] unknown condition '{cond}' for post {post['id']} — treating as eligible", file=sys.stderr)
        return True
    return handler()


def pick_next_post(posts, state):
    """最後に使った日が古い順 → 一度も使ってないやつ優先.
    ただし condition を満たさない post はスキップ.
    全部失格なら history に依存せず最古を返す (フォールバック)."""
    history = state.get("history", {})

    def last_used(post_id):
        return history.get(post_id, "1970-01-01")

    sorted_posts = sorted(posts, key=lambda p: last_used(p["id"]))
    for p in sorted_posts:
        if is_eligible(p):
            return p
    # フォールバック: 条件無視で最古を返す (起きないはずだが安全側)
    print("[warn] 全 post が condition 不適合 — フォールバックで最古を選択", file=sys.stderr)
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

    # 履歴更新 (どこか1つでも成功してたら記録 = 同パターンが翌日また選ばれない)
    successes = [v for v in results.values() if "ERROR" not in str(v) and v != "SKIPPED: no image"]
    if successes:
        state.setdefault("history", {})[post["id"]] = today
        save_state(state)

    print(f"Results: {results}")

    # 終了コード: いずれかの ENABLED プラットフォームが ERROR なら 1 を返す.
    # これにより GitHub Actions のジョブが failure になり、リポジトリの
    # 通知設定で持ち主にメールが来る (= 投稿失敗にすぐ気づける).
    # SKIPPED (画像なし) は失敗扱いしない.
    errors = [(k, v) for k, v in results.items() if isinstance(v, str) and v.startswith("ERROR")]
    if errors:
        print("\n!! FAILED platforms:", file=sys.stderr)
        for platform, msg in errors:
            print(f"  - {platform}: {msg}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
