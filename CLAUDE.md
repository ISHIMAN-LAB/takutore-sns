# 卓トレ高田馬場店 SNS月次投稿生成ルーティン

このリポジトリでスケジュール実行されるエージェントは、翌月分のX + Google投稿を生成してmainにpushする。

---

## 手順

### 1. 翌月のyyyy-mmを決定
`date -u +%Y-%m-%d` で今日の日付を確認、翌月を計算。
出力先: `posts_<yyyy-mm>.md`。既にあれば `posts_<yyyy-mm>-v2.md` で保存。

### 2. 参照ファイルを必ず読む
- `README.md` — ルール: 会員数・創業年数・Google評価を出さない
- `posts_june_2026.md` — X投稿出力フォーマットの正典
- `google_post_2026-05-29.md` — Google投稿の正典
- `images/pool/README.md` — 画像プールの説明

### 3. 画像プールを把握
`images/pool/` 配下の全ファイルを `ls` で確認 → 候補を5〜8枚に絞ってReadで内容確認。
過去月で使った画像も再利用OK。同月内では重複させない。

### 4. テーマ設計
**X用 8〜9本** (火・金の週2回ペース)。翌月の季節・イベントを主軸に。
**Google用 2本**: 月前半 (1〜10日) と後半 (20〜末) に1本ずつ。
Googleは初見ユーザー前提で店舗基本情報 (24時間365日・無人・高田馬場駅徒歩圏・予約即時・ロボット練習機あり) + 月フックを必ず入れる。

### 5. posts_<yyyy-mm>.md を生成
`posts_june_2026.md` のフォーマットに完全に揃える:
- 冒頭: 月概要 + ルール再記 + 画像ディレクトリパス
- カレンダー早見表テーブル (X用 + Google用)
- X 各投稿セクション: 日時・テーマ・画像パス・本文 (コードブロック内)
- Google 各投稿セクション: 画像パス・本文 (コードブロック内) + CTA
- 運用メモ

### 6. コピペ用フォルダを生成 ← 毎回必須
`posts_<yyyy-mm>/` フォルダを作り、各投稿の本文だけを入れた .txt ファイルを1本1ファイルで作成。
ファイル名規則: `X01_MMDD曜HHMM_テーマ略称.txt` / `G01_MMDD曜HHMM_Google前半.txt`
ファイル内容: 投稿テキストのみ (マークダウン・コードブロック不要。そのままコピペできる状態)。

### 7. ルール厳守
- ❌ 会員数を出さない
- ❌ 創業年数を出さない
- ❌ Google評価を出さない
- 画像パスは `images/pool/<filename>` で記載
- X本文は140〜280字、ハッシュタグ含む
- Google本文は300〜500字推奨

### 8. commit & push
```bash
git add posts_<yyyy-mm>.md posts_<yyyy-mm>/
git -c user.email='takutore-bot@noreply.anthropic.com' -c user.name='takutore-monthly-bot' \
    commit -m 'Add posts plan for <yyyy-mm>'
git push -u origin main
```

### 9. Gmail通知
`mcp__Gmail__create_draft` で `kaz_tk4_mix0223@hotmail.com` 宛に完了通知を送る。
件名: `【卓トレ高田馬場】<yyyy年M月>分 X+Google投稿プラン 生成完了`
本文: 生成した投稿本数・テーマ一覧・注意点のサマリー。

---

## フォルダ構成イメージ (例: 2026-07)

```
posts_2026-07.md          # プランマスター (テーマ・画像・コピー)
posts_2026-07/
├── X01_0703金1830_梅雨明け.txt
├── X02_0707火2000_七夕.txt
├── ...
├── X09_0731金2030_7月締め.txt
├── G01_0705日1700_Google前半.txt
└── G02_0722水1800_Google後半.txt
```
