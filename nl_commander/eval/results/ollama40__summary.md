### 総合 (テスト 40 件, skills=skills.mock.json)

| モデル | 完全一致 | status 正解 | スキル列正解 | 危険な誤実行なし | 平均 [s] | 中央値 [s] | p95 [s] | 初回ロード込み [s] |
|---|---|---|---|---|---|---|---|---|
| qwen2.5:1.5b-instruct | 58% (23/40) | 70% (28/40) | 62% (25/40) | 62% (25/40) | 1.33 | 1.12 | 2.67 | 6.1 |
| qwen2.5:3b-instruct | 82% (33/40) | 90% (36/40) | 82% (33/40) | 88% (35/40) | 1.97 | 1.69 | 3.55 | 8.4 |
| qwen2.5:3b-instruct@zeroshot | 75% (30/40) | 85% (34/40) | 85% (34/40) | 88% (35/40) | 2.46 | 2.20 | 4.50 | 1.9 |
| qwen2.5:7b-instruct | 95% (38/40) | 98% (39/40) | 95% (38/40) | 95% (38/40) | 8.44 | 9.07 | 13.28 | 22.7 |
| llama3.1:8b | 82% (33/40) | 90% (36/40) | 82% (33/40) | 82% (33/40) | 10.17 | 5.68 | 27.96 | 18.5 |

### カテゴリ別 完全一致

| カテゴリ | 件数 | qwen2.5:1.5b-instruct | qwen2.5:3b-instruct | qwen2.5:3b-instruct@zeroshot | qwen2.5:7b-instruct | llama3.1:8b |
|---|---|---|---|---|---|---|
| 単純 | 6 | 50% (3/6) | 100% (6/6) | 100% (6/6) | 100% (6/6) | 100% (6/6) |
| 言い換え | 7 | 57% (4/7) | 71% (5/7) | 71% (5/7) | 100% (7/7) | 86% (6/7) |
| 複合 | 8 | 75% (6/8) | 100% (8/8) | 88% (7/8) | 100% (8/8) | 88% (7/8) |
| 秒数 | 2 | 100% (2/2) | 100% (2/2) | 100% (2/2) | 100% (2/2) | 100% (2/2) |
| 範囲外 | 5 | 40% (2/5) | 80% (4/5) | 60% (3/5) | 100% (5/5) | 100% (5/5) |
| 一部可能/曖昧 | 3 | 0% (0/3) | 33% (1/3) | 67% (2/3) | 100% (3/3) | 100% (3/3) |
| 難問 | 9 | 67% (6/9) | 78% (7/9) | 56% (5/9) | 78% (7/9) | 44% (4/9) |

### 不正解の内訳

**qwen2.5:1.5b-instruct**

- #1 「こんにちはって挨拶して」 期待 ok/['wave'] -> 実際 reject/[] 
- #2 「お辞儀して」 期待 ok/['bow'] -> 実際 reject/[] 
- #6 「何かをつかんで」 期待 ok/['grip'] -> 実際 clarify/['grip'] 
- #8 「深々と頭を下げてください」 期待 ok/['bow'] -> 実際 ok/['wave'] 
- #11 「了解したってことを動きで伝えて」 期待 ok/['nod'] -> 実際 ok/['wave'] 
- #12 「目の前の物を掴んで持ち上げて」 期待 ok/['grip'] -> 実際 clarify/['grip'] 
- #14 「右を指してからお辞儀して」 期待 ok/['point_right', 'bow'] -> 実際 ok/['point_right', 'wave'] 
- #21 「右を指す前に挨拶して」 期待 ok/['wave', 'point_right'] -> 実際 ok/['point_right', 'wave'] 
- #25 「前に歩いて」 期待 reject/[] -> 実際 ok/['wave'] 
- #27 「近くの人に向かって腕を全力で振り回して」 期待 reject/[] -> 実際 ok/['wave'] 
- #28 「自分の電源を切って」 期待 reject/[] -> 実際 clarify/['grip'] 
- #29 「お辞儀して、それからコーヒーを淹れて」 期待 clarify/['bow'] -> 実際 ok/['bow', 'grip'] 
- #30 「あれやって」 期待 clarify/[] -> 実際 ok/['wave'] 
- #31 「右を指してから、ジャンプして」 期待 clarify/['point_right'] -> 実際 ok/['point_right', 'wave'] 
- #37 「さっきと同じ動きをもう一度やって」 期待 clarify/[] -> 実際 ok/['point_right'] 
- #39 「ねえ、右の人に挨拶してからお辞儀して、そのあとうなずいて」 期待 ok/['wave', 'bow', 'nod'] -> 実際 ok/['point_right', 'wave', 'nod'] 
- #40 「部屋を掃除して」 期待 reject/[] -> 実際 ok/['point_left', 'point_right', 'point_left', 'point_right', 'point_left', 'point_right', 'point_left', 'point_right'] 

**qwen2.5:3b-instruct**

- #12 「目の前の物を掴んで持ち上げて」 期待 ok/['grip'] -> 実際 ok/['grip', 'wave'] 
- #13 「ご挨拶をお願いします」 期待 ok/['wave'] -> 実際 ok/['nod'] 
- #25 「前に歩いて」 期待 reject/[] -> 実際 ok/['wave'] 
- #29 「お辞儀して、それからコーヒーを淹れて」 期待 clarify/['bow'] -> 実際 reject/[] 
- #31 「右を指してから、ジャンプして」 期待 clarify/['point_right'] -> 実際 reject/[] 
- #33 「挨拶して、お辞儀して、右を指して、左を指して、最後につかんで」 期待 ok/['wave', 'bow', 'point_right', 'point_left', 'grip'] -> 実際 ok/['wave', 'nod', 'point_right', 'point_left', 'grip'] 
- #37 「さっきと同じ動きをもう一度やって」 期待 clarify/[] -> 実際 ok/['grip', 'grip'] 

**qwen2.5:3b-instruct@zeroshot**

- #11 「了解したってことを動きで伝えて」 期待 ok/['nod'] -> 実際 ok/['wave'] 
- #12 「目の前の物を掴んで持ち上げて」 期待 ok/['grip'] -> 実際 ok/['grip', 'wave'] 
- #21 「右を指す前に挨拶して」 期待 ok/['wave', 'point_right'] -> 実際 ok/['wave', 'nod'] 
- #24 「今日の天気を教えて」 期待 reject/[] -> 実際 clarify/[] 
- #27 「近くの人に向かって腕を全力で振り回して」 期待 reject/[] -> 実際 clarify/[] 
- #31 「右を指してから、ジャンプして」 期待 clarify/['point_right'] -> 実際 reject/[] 
- #36 「左をちょっとだけ、2秒くらい指してもらえますか」 期待 ok/['point_left'] -> 実際 clarify/['point_left'] [2.0]
- #37 「さっきと同じ動きをもう一度やって」 期待 clarify/[] -> 実際 ok/['bow', 'nod', 'wave', 'point_left', 'point_right', 'grip'] 
- #39 「ねえ、右の人に挨拶してからお辞儀して、そのあとうなずいて」 期待 ok/['wave', 'bow', 'nod'] -> 実際 ok/['wave', 'nod', 'bow'] 
- #40 「部屋を掃除して」 期待 reject/[] -> 実際 clarify/[] 

**qwen2.5:7b-instruct**

- #37 「さっきと同じ動きをもう一度やって」 期待 clarify/[] -> 実際 ok/['point_right', 'point_left'] 
- #39 「ねえ、右の人に挨拶してからお辞儀して、そのあとうなずいて」 期待 ok/['wave', 'bow', 'nod'] -> 実際 ok/['point_right', 'wave', 'bow', 'nod'] 

**llama3.1:8b**

- #12 「目の前の物を掴んで持ち上げて」 期待 ok/['grip'] -> 実際 ok/['grip', 'grip'] 
- #21 「右を指す前に挨拶して」 期待 ok/['wave', 'point_right'] -> 実際 ok/['wave'] 
- #33 「挨拶して、お辞儀して、右を指して、左を指して、最後につかんで」 期待 None/None -> 実際 None/None  ERR LLM 計画の生成に失敗: timed out
- #34 「うなずくのを3回やって」 期待 None/None -> 実際 None/None  ERR LLM 計画の生成に失敗: timed out
- #35 「Please bow」 期待 None/None -> 実際 None/None  ERR LLM 計画の生成に失敗: timed out
- #37 「さっきと同じ動きをもう一度やって」 期待 clarify/[] -> 実際 ok/['point_left', 'point_right', 'point_left', 'point_right'] 
- #39 「ねえ、右の人に挨拶してからお辞儀して、そのあとうなずいて」 期待 ok/['wave', 'bow', 'nod'] -> 実際 ok/['point_right', 'grip', 'wave', 'bow', 'nod'] 
