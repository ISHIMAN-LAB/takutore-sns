#!/usr/bin/env bash
# launchd / cron から呼ばれるエントリポイント.
# トークンを必要なら更新し、変更があれば GH Secrets に同期する.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Homebrew の gh を見つけるため (launchd の PATH は最小)
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

cd "$SCRIPT_DIR"

ts() { date -u "+%Y-%m-%dT%H:%M:%SZ"; }

# 1. refresh: 残14日未満なら更新
out=$(/usr/bin/python3 "$SCRIPT_DIR/refresh_token.py" 2>&1 || true)
echo "[$(ts)] refresh: $out"

# REFRESHED が出ていれば secret 同期
if echo "$out" | grep -q '^REFRESHED'; then
    sync_out=$(bash "$SCRIPT_DIR/sync_secrets.sh" 2>&1 || true)
    echo "[$(ts)] sync: $sync_out"
fi
