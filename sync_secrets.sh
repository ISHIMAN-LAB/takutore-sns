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

# .env をロード (export せずに連想配列に入れる)
declare -A ENV
while IFS='=' read -r key value; do
    [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
    key="${key// /}"
    ENV["$key"]="$value"
done < "$ENV_FILE"

# 同期対象 (変動する値)
SYNC_KEYS=(IG_ACCESS_TOKEN IG_TOKEN_EXPIRES_AT FB_PAGE_ACCESS_TOKEN)

echo "Target repo: $REPO"
for key in "${SYNC_KEYS[@]}"; do
    val="${ENV[$key]:-}"
    if [[ -z "$val" ]]; then
        echo "  SKIP $key (空)"
        continue
    fi
    if gh secret set "$key" --repo "$REPO" --body "$val" >/dev/null 2>&1; then
        len="${#val}"
        echo "  OK   $key (len=$len)"
    else
        echo "  FAIL $key (gh secret set 失敗)" >&2
        exit 2
    fi
done

echo "Done."
