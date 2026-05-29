# 画像プール

手動投稿 (X / Google) で使う候補写真の置き場。
毎月20日に走る `monthly-posts-generator` ルーティンが、ここの画像を直接Readして内容を見ながら選定する。

## 追加・更新の手順

新しい写真を撮ったら:

```bash
cp <写真パス> ~/takutore-sns/images/pool/
cd ~/takutore-sns
git add images/pool/
git commit -m "Add photos to pool"
git push
```

## 注意

- 1ファイル100MB超はGitHub側で拒否される (現状ぜんぶ10MB以下)
- 古くて使わない写真は `git rm` で消す。`.gitignore`に書くだけでは履歴に残る
- このプールと `images/01-xxx.jpg 〜 12-xxx.jpg` (自動投稿用ペア) は別物
