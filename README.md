# 卓トレ高田馬場店 SNS自動投稿システム

X (Twitter) / Instagram / Facebook に定期投稿を自動配信するシステム。
GitHub Actions cron + Python で構成。サーバー不要、ほぼ無料。

## 動く仕組み

```
┌─────────────────────────────────────────────────┐
│ GitHub Actions cron (月・水・金 19:30 JST)       │
│   ↓                                              │
│ poster.py が起動                                 │
│   ↓                                              │
│ posts.json から最近使ってない投稿を選択           │
│   ↓                                              │
│ X / Facebook / Instagram に並列投稿              │
│   ↓                                              │
│ state.json に使用履歴を記録 → repoにcommit back  │
└─────────────────────────────────────────────────┘
```

## ファイル構成

```
takutore-sns/
├── posts.json            # 投稿コンテンツ12パターン (編集可)
├── state.json            # 自動生成: 使用履歴
├── poster.py             # メインスクリプト
├── platforms/
│   ├── x_client.py       # X (Twitter) 投稿
│   ├── facebook_client.py
│   └── instagram_client.py
├── images/               # 投稿画像 (01-xxx.jpg ...)
├── requirements.txt
├── .github/workflows/
│   └── post.yml          # cron設定
├── .env.example          # ローカルテスト用テンプレ
└── README.md             # ← これ
```

---

## セットアップ手順 (この順番で)

### Phase 0: GitHub準備 (5分)

1. このディレクトリをGitHubにPush (**プライベートリポジトリ推奨**)
   ```bash
   cd takutore-sns
   git init
   git add .
   git commit -m "Initial commit"
   gh repo create takutore-sns --private --source=. --push
   ```
2. Settings → Actions → General → Workflow permissions → **Read and write** を有効化

### Phase 1: Facebook Page投稿 (一番ラク・最初に動かす)

1. **Facebookページ作成** (まだなければ): https://www.facebook.com/pages/create
2. **Meta for Developers** でアプリ作成: https://developers.facebook.com/
   - "Business" タイプで作成
3. **Graph API Explorer** で以下のトークンを取得:
   - `pages_manage_posts`, `pages_read_engagement` 権限
   - 短期ユーザートークン → 長期トークン → **ページトークン** に変換
   - 手順: https://developers.facebook.com/docs/facebook-login/guides/access-tokens
4. **取得した値**:
   - `FB_PAGE_ID`: ページのID (ページ "About" 欄で確認)
   - `FB_PAGE_ACCESS_TOKEN`: 長期化したページトークン
5. GitHub repoの **Settings → Secrets and variables → Actions** に2つを登録

### Phase 2: Instagram Business投稿 (画像必須)

**前提**: Instagramアカウントを「ビジネス」または「クリエイター」に切り替え + Facebookページに連携

1. Meta Developer App で **Instagram Graph API** を有効化
2. **画像のホスト方法**: GitHub repo内の`images/`をRaw URLで参照
   - 例: `https://raw.githubusercontent.com/USERNAME/takutore-sns/main`
3. **取得する値**:
   - `IG_USER_ID`: IGビジネスアカウントID (Graph API Explorerで `/me/accounts?fields=instagram_business_account`)
   - `IG_ACCESS_TOKEN`: ページトークン (FBと同じものでOK)
   - `IMAGE_BASE_URL`: 上記Raw URLのルート
4. GitHub Secretsに登録

### Phase 3: X (Twitter) 投稿

1. https://developer.x.com/ で開発者アカウント作成
2. **2026年2月以降は新規無料枠なし**: pay-per-use登録 (投稿1件 約$0.01)
3. プロジェクト → アプリ作成 → **Read and Write** 権限
4. **取得する値**:
   - `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`
5. GitHub Secretsに登録

### Phase 4: 画像準備

`images/01-24h-deep-night.jpg` 〜 `images/12-access.jpg` を入れる。
各 `posts.json` の `image_hint` フィールドが撮影方針。

**画像なしでも動作する**: X/FBはテキストのみで投稿される。**IGだけスキップ**される。

---

## 動作確認

### ローカルでドライラン

```bash
cp .env.example .env
# .env を編集して DRY_RUN=true のまま
pip install -r requirements.txt
set -a; source .env; set +a
python poster.py
```

→ 「次に投稿されるパターン」が表示される。

### GitHub Actionsで手動実行

repoの **Actions タブ → SNS Auto Post → Run workflow** で `dry_run: true` 選んで実行。

### 本番投稿開始

`.env`の`DRY_RUN=false`に変更 → 自動で月・水・金 19:30に動き出す。

---

## Claude Codeに渡す指示書

このプロジェクトをClaude Codeで拡張・カスタマイズするときの起動プロンプト例:

```
このリポジトリは卓トレ高田馬場店のSNS自動投稿システムです。
README.md を読んでから、以下のタスクを進めてください:

【現在の状態】
- posts.json に12パターンの投稿が既に入っている
- poster.py がローテーション選択を担当
- platforms/ に X / FB / IG のクライアントがある

【今やりたいこと】
(ここに具体的なタスクを書く。例: 下記から選択)

- [ ] 投稿パターンを5つ追加したい (テーマ: ◯◯, ◯◯, ...)
- [ ] Reservaの空き枠と連動した突発投稿スクリプトを別途追加
- [ ] 投稿失敗時にSlackに通知する仕組みを追加
- [ ] 画像をAIで自動生成 (DALL-E等) して images/ に保存
- [ ] 投稿後のエンゲージメント(いいね数等)を集計するレポート
- [ ] Threadsにも対応

実装前に、現状のコードを読んで設計案を提示してください。
```

---

## カスタマイズしやすいポイント

| やりたいこと | 編集する場所 |
|---|---|
| 投稿時刻を変える | `.github/workflows/post.yml` の `cron:` |
| 投稿頻度を増減 | 同上 (cron式) |
| 投稿パターンを追加 | `posts.json` に1要素追加 |
| 特定パターンを停止 | `posts.json` の該当`enabled: false` |
| 一時的にX/FB/IGを止める | repo Settings → Variables で `ENABLE_X=false` 等 |

---

## トラブルシューティング

**Q: IG投稿が失敗する**
→ IGがビジネス垢になってない / FBページに連携してない / 画像URLが公開されてない、のどれか。`IMAGE_BASE_URL` をブラウザで叩いて画像が見えるか確認。

**Q: Xが認証エラー**
→ 4つのキーのうち`ACCESS_TOKEN`系は「ユーザーコンテキスト」用。アプリのSettings → User authentication settings で Read and Write になってるか確認。

**Q: state.jsonがcommitされない**
→ Settings → Actions → General → Workflow permissions が `Read and write` になってない。

---

## 運用メモ

- **月・水・金の週3回**ペースで12パターンなら4週間で一周
- 季節ネタ(GW・夏休み・年末年始)は別途突発投稿で混ぜる
- `posts.json` の更新は普通にgit commitで反映される
- 投稿の良し悪しは1ヶ月運用してエンゲージメント比較で判断する

---

## ルール (LP・マーケ全般共通)

- ❌ 会員数を表示しない (変動するため)
- ❌ 創業年数を出さない
- ❌ Google評価を出さない

`posts.json` 編集時もこれを守る。
