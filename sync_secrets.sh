#!/usr/bin/env bash
# Push current .env values to GitHub repo secrets.
#
# Requires: gh CLI authenticated with `repo` scope.
# Usage: ./sync_secrets.sh [REPO]
#   REPO defaults to ISHIMAN-LAB/takutore-sns
#
# 同期対象は「期限付き or 値が変わりうる」secret のみ.
# 不変な FB_APP_ID / IG_USER_ID / FB_PAGE_ID は初回のみ手動で gh secret set してOK.

set -euo pipefail

REPO="${1:-ISHIMAN-LAB/takutore-sns}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: $ENV_FILE がありません" >&2
    exit 1
fi

# 同期対象 (変動する値)
SYNC_KEYS="IG_ACCESS_TOKEN IG_TOKEN_EXPIRES_AT FB_PAGE_ACCESS_TOKEN"

echo "Target repo: $REPO"
for key in $SYNC_KEYS; do
    # `KEY=VALUE` 行から VALUE を抽出 (最初に一致した行のみ, # 行は無視)
    val=$(grep -m1 "^${key}=" "$ENV_FILE" | cut -d= -f2- || true)
    if [[ -z "$val" ]]; then
        echo "  SKIP $key (空 or .env に無し)"
        continue
    fi
    if gh secret set "$key" --repo "$REPO" --body "$val" >/dev/null 2>&1; then
        echo "  OK   $key (len=${#val})"
    else
        echo "  FAIL $key (gh secret set 失敗)" >&2
        exit 2
    fi
done

echo "Done."
