# Claude Code 引継ぎ: 卓トレ高田馬場店 SNS自動投稿セットアップ

## このドキュメントの使い方

Claude Codeでターミナルを開き、このディレクトリで以下のように起動:

```bash
claude
```

起動したら、最初のプロンプトとして以下を貼り付け:

```
このディレクトリの HANDOFF.md と README.md を読んでから、
HANDOFF.md の「今後のタスク」セクションを参考に作業してください。
シークレット値は実行時に対話で聞いてください。
```

---

## 現状サマリー (2026-05-25 時点)

### 達成済み

| 項目 | 状態 | 値 |
|---|---|---|
| Meta開発者アカウント | ✅ | (作成済み) |
| アプリ作成 | ✅ | アプリ名: `takutore-sns-poster` |
| **App ID** | ✅ | `1470442400955331` |
| **App Secret** | ✅ | `.env` に保管 |
| Instagram ビジネスアカウント連携 | ✅ | `takutoretakadanobaba` (followers: 203) |
| **IG_USER_ID** | ✅ | `17841423440462973` |
| **長期ユーザートークン (~60日)** | ✅ | `.env` に保管 (期限 2026-07-24) |
| **トークン自動更新 (launchd 週次)** | ✅ | `~/Library/LaunchAgents/com.takutore.refresh-ig-token.plist` |
| **トークン投稿前自動更新 (lazy)** | ✅ | `post_ig.py` / `post_fb.py` 起動時に実行 |
| Facebook ページ連携 | ✅ | `卓トレ　高田馬場店` |
| **FB_PAGE_ID** | ✅ | `109095650463255` |
| **FB_PAGE_ACCESS_TOKEN (永続)** | ✅ | `.env` に保管 (`expires_at=0`) |
| IG 単発投稿スクリプト | ✅ | [post_ig.py](post_ig.py) |
| FB 単発投稿スクリプト | ✅ | [post_fb.py](post_fb.py) |
| IG 実投稿テスト | ✅ | 1件投稿済み (`https://www.instagram.com/p/DYvqLDyCSgc/` ・要手動削除) |
| GitHub Repo (PUBLIC) | ✅ | https://github.com/ISHIMAN-LAB/takutore-sns |
| GH Secrets (8件) | ✅ | FB_APP_ID, FB_APP_SECRET, IG_USER_ID, IG_ACCESS_TOKEN, IG_TOKEN_EXPIRES_AT, FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN, IMAGE_BASE_URL |
| GH Actions workflow | ✅ | M/W/F 19:30 JST, DRY_RUN=true デフォルトで安全 |
| 投稿画像 (5/12 枚) | ⚠️ 仮置き | 03 雨, 05 朝活, 06 一人練習, 09 初心者, 11 予約 (全部 Unsplash 仮置き — 実撮影で差し替え予定) |
| 投稿画像 (残り 7/12 枚) | ❌ | 01 深夜店内, 02 ロボット, 04 ビジネスバッグ, 07 店内2台, 08 大会前, 10 親子, 12 店の入口 (実撮影が必要 — 未準備な投稿は IG ではスキップされ FB はテキストのみ投稿される) |

### 保留中

- **X (Twitter)**: Basic プラン $200/月 が必要なため当面見送り (代替案として Threads も保留)
- **FB 実投稿テスト**: `post_fb.py --no-dry-run` をいつでも実行可能 (実投稿は和英さんの GO 後に)
- **本番稼働切替**: `gh variable set DRY_RUN --body false` を実行すると次の cron から実投稿開始
- **画像実撮影**: 7枚 (01,02,04,07,08,10,12) を `posts.json` の `image_hint` に従って撮影して `images/` に commit

### 重要な訂正

旧 HANDOFF にあった App ID `1711204020229016` は **誤記** だった。トークン introspection の結果、正しくは **`1470442400955331`** (`takutore-sns-poster`)。`.env` には正しい値が入っている。

---

## ファイル構成 (主要)

```
takutore-sns/
├── .env                 # シークレット (gitignore済み, mode 600)
├── .env.example         # テンプレ
├── .gitignore
├── HANDOFF.md           # このファイル
├── README.md
├── post_ig.py           # IG 単発投稿 (--dry-run デフォルト)
├── post_fb.py           # FB 単発投稿 (--dry-run デフォルト)
├── refresh_token.py     # 長期トークン延長 (--force / 残14日未満で自動)
├── poster.py            # ローテーション制御 (GHA cron 用)
├── posts.json           # 12パターンの投稿コンテンツ
├── state.json           # 自動生成: 使用履歴
├── platforms/
│   ├── x_client.py
│   ├── facebook_client.py
│   └── instagram_client.py
├── images/              # 投稿画像 (まだ未配置)
├── requirements.txt
└── .github/workflows/post.yml
```

加えて: `~/Library/LaunchAgents/com.takutore.refresh-ig-token.plist` (launchd ジョブ定義)

---

## `.env` の構造 (現在)

```
FB_APP_ID=1470442400955331
FB_APP_SECRET=<32桁hex>
IG_USER_ID=17841423440462973
IG_ACCESS_TOKEN=<長期トークン ~210文字>
IG_TOKEN_EXPIRES_AT=<ISO8601 UTC>
FB_PAGE_ID=109095650463255
FB_PAGE_ACCESS_TOKEN=<Page Token, 永続>
```

`refresh_token.py` の自動実行で `IG_ACCESS_TOKEN` と `IG_TOKEN_EXPIRES_AT` が定期的に書き換わる。
`FB_PAGE_ACCESS_TOKEN` は永続なので更新不要 (ただし `IG_ACCESS_TOKEN` が完全失効すると連動失効するので、ユーザートークンを生かし続けることが必須)。

---

## 自動更新の仕組み

| レイヤ | 仕組み | トリガ | 動作 |
|---|---|---|---|
| L1: lazy refresh | `post_ig.py` / `post_fb.py` 起動時に `refresh_token.py` を subprocess で呼ぶ | 投稿のたび | 残14日未満なら更新、そうでなければ即スキップ |
| L2: スケジューラ | macOS launchd (`com.takutore.refresh-ig-token`) | 毎週日曜 03:00 | 同上 |
| L3: 手動 | `python3 refresh_token.py --force` | 任意 | 必ず更新 |

確認コマンド:
```bash
launchctl list | grep takutore           # PID列 "-" は待機中
cat /tmp/com.takutore.refresh-ig-token.log
python3 refresh_token.py                  # 残日数チェック (--force で強制)
```

止めたい場合:
```bash
launchctl unload -w ~/Library/LaunchAgents/com.takutore.refresh-ig-token.plist
```

---

## 単発投稿コマンド (動作確認用)

```bash
# IG ドライラン (コンテナ作成までで停止)
python3 post_ig.py --image-url https://picsum.photos/1080/1080 --caption "テスト #卓トレ"

# IG 実投稿
python3 post_ig.py --image-url https://example.com/foo.jpg --caption "本文" --no-dry-run

# FB テキストのみドライラン
python3 post_fb.py --message "テスト投稿"

# FB 画像付き実投稿
python3 post_fb.py --message "本文" --image-url https://example.com/foo.jpg --no-dry-run
```

---

## 今後のタスク

### 1. GitHub Actions 統合 (`poster.py` 経由の自動 cron 投稿)

[README.md](README.md) の Phase 0 〜 4 を参照. 必要な作業:

- `git init` してリポジトリ化
- GitHub にプライベートリポジトリとして push
- Settings → Secrets and variables → Actions に以下を登録:
  - `FB_APP_ID`, `FB_APP_SECRET`
  - `IG_USER_ID`, `IG_ACCESS_TOKEN`
  - `FB_PAGE_ID`, `FB_PAGE_ACCESS_TOKEN`
  - `IMAGE_BASE_URL` (= `https://raw.githubusercontent.com/<USER>/takutore-sns/main`)
- `images/01-xxx.jpg` 〜 `images/12-xxx.jpg` を commit
- GH Actions 上での **トークン自動更新**: `refresh_token.py` を毎週 cron で走らせ、新トークンを `gh secret set` で更新する補助ワークフローを追加 (このリポジトリの `IG_ACCESS_TOKEN` が GHA Secret なら、GHA から自身の Secret を書き換える権限が必要)
- 手動実行 (`Actions タブ → SNS Auto Post → Run workflow` で `dry_run: true`) で動作確認

### 2. X (Twitter) セットアップ

- https://developer.x.com/ で開発者アカウント作成
- pay-per-use 登録 (1投稿 ~$0.01)
- アプリ作成 → Read and Write 権限
- 4つのキーを取得して `.env` / GH Secrets に登録: `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`

### 3. 投稿画像の準備

`images/01-24h-deep-night.jpg` 〜 `images/12-access.jpg` を撮影・配置.
`posts.json` の各エントリの `image_hint` フィールドが撮影方針.

---

## トラブルシューティング

### トークンが死んだら

```bash
# 1. 現状確認
python3 -c "import json,urllib.request,urllib.parse,os; \
  d={k:v for k,v in (l.split('=',1) for l in open('.env') if '=' in l and not l.startswith('#'))}; \
  r=urllib.request.urlopen('https://graph.facebook.com/debug_token?'+urllib.parse.urlencode({'input_token':d['IG_ACCESS_TOKEN'].strip(),'access_token':d['IG_ACCESS_TOKEN'].strip()})); \
  print(json.loads(r.read()))"

# 2. 完全失効していたら Graph API Explorer から短期トークン再取得
#    https://developers.facebook.com/tools/explorer/
#    アプリ: takutore-sns-poster (1470442400955331) を必ず選択
#    権限: pages_show_list, pages_read_engagement, pages_manage_posts,
#         instagram_basic, instagram_content_publish
#    取得後、refresh_token.py の代わりに exchange_token フローを再実行 (HANDOFF 履歴参照)
```

### `me/accounts` が空 (ユーザーが Page 直接管理者でない問題)

これは既知だが、`/{page_id}?fields=access_token` でページトークンは取れることが今回判明 (`pages_show_list` スコープに該当ページの target_id が含まれていればOK)。気にしなくてよい.

### IG コンテナ作成エラー

- 画像 URL が HTTPS で公開アクセス可能か確認
- 画像サイズが極端に大きすぎないか (Instagram の制限内に)
- container_id は 24h で自動失効するので、作成後すぐに publish に進むこと

---

## 連絡事項

- **会員数、創業年数、Google評価は投稿内容に絶対に入れない** (運用ルール)
- 投稿の検証時、`posts.json` の1番目 (24時間営業×深夜) を使うのが画像準備済みでなくテキストだけでも分かりやすい
- 画像URLが用意できていない場合、Instagram投稿は画像必須なので、テスト用にダミー画像 (例: `https://picsum.photos/1080/1080`) を使ってよい
