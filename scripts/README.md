# 野菜・果物ショート動画 台本集

シリーズ名：**「知らなかった！野菜と果物のヒミツ」**

- 形式：縦型 9:16（Instagram リール / TikTok / YouTube ショート）
- 尺：1本 20〜30秒
- 構成：①フック（0〜3秒）→ ②ヒミツの紹介 → ③驚き・オチ → ④保存・フォロー誘導
- 映像：AI動画生成（各カットに英語の生成プロンプト付き）
- 音声：ナレーション（明るい女性 or 男性の声）＋ ポップなBGM ＋ 効果音

| # | 題材 | タイトル | ファイル |
|---|------|----------|----------|
| 1 | みかん | みかんの房の数、むく前にわかる？ | [01_mikan.md](01_mikan.md) |
| 2 | ブロッコリー | 実は「つぼみ」を食べている | [02_broccoli.md](02_broccoli.md) |
| 3 | いちご | つぶつぶの正体は… | [03_ichigo.md](03_ichigo.md) |
| 4 | バナナ | 茶色い点は捨てるサインじゃない | [04_banana.md](04_banana.md) |
| 5 | トマト | 甘いトマトはお尻で見分ける | [05_tomato.md](05_tomato.md) |

## 共通ルール

- 生成プロンプト末尾に共通スタイルを付ける：
  `vertical 9:16, macro food photography, soft natural light, shallow depth of field, clean white wooden table, vibrant colors, 4k, smooth slow motion`
- テロップ：太字の丸ゴシック、白文字＋濃い縁取り、画面中央〜上部
- 「〜と言われています」など、断定しすぎない表現にする
- 最後のカットは毎回同じ締め（「保存して誰かに教えてあげてね！」）でシリーズ感を出す

## 動画

| # | 動画 | 作り方 |
|---|------|--------|
| 1 | `video/out/mikan.mp4`（約29秒） | `python3 video/make_mikan.py` |
| 2 | `video/out/broccoli.mp4`（約28秒） | `python3 video/make_broccoli.py` |
| 3 | `video/out/ichigo.mp4`（約19秒） | `python3 video/make_ichigo.py` |
| 4 | `video/out/banana.mp4`（約23秒） | `python3 video/make_banana.py` |
| 5 | `video/out/tomato.mp4`（約19秒） | `python3 video/make_tomato.py` |

- 投稿用のタイトル・説明文・ハッシュタグは [`video/posts.md`](../video/posts.md)
- #2〜#5 は共通エンジン `video/engine.py` で作っている（シーンを並べるだけで、セリフの長さに合わせてシーンの長さが自動で決まる）。#1 は単独のスクリプト。
- 必要なもの：Python3、Pillow、numpy、ffmpeg、IPAゴシックフォント、Open JTalk（`apt install open-jtalk open-jtalk-mecab-naist-jdic`）
- 案内役は柴犬のキャラクター「コロ」。セリフはOpen JTalkで読み上げ、口パクを音声の大きさに合わせて動かす。
- イラスト・テロップ・BGM・効果音はすべてスクリプト内で生成。声が出ている間はBGMを自動で下げる。
- 声のモデル：東北大学 知的通信ネットワーク研究室「HTS voice tohoku-f01」（happy、CC BY 4.0）。`video/voices/` に同梱。動画を投稿するときは説明欄などにクレジットを入れる。
  - クレジット例：`音声：HTS voice tohoku-f01（東北大学 伊藤・能勢研究室, CC BY 4.0）`
