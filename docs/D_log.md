# ストリームD ログ（自然言語コマンダー / ローカル LLM）

## 2026-11-01 13:30 環境確認・セットアップ
- Ollama: Windows 側 `ollama.exe serve`(PID 4508) が 127.0.0.1:11434 のみ listen。ロード中モデルなし(`ollama ps` 空)、他作業で未使用と判断し停止。
- 再起動: `OLLAMA_HOST=0.0.0.0:11434 OLLAMA_KEEP_ALIVE=30s ollama serve` を PowerShell から非表示で起動(PID 181968)。
  - ハマり: トレイアプリ(`ollama app.exe`)が 127.0.0.1 側で自動的に別 serve(PID 47028)を再起動した。→ 0.0.0.0 側(自分のプロセス)は 127.0.0.1 以外のアドレス経由で使われる。localhost 宛はトレイ側。モデル保管先は共通。
  - WSL2(NAT モード)から `localhost:11434` は届かない。ゲートウェイ IP(`ip route` の default, 今回 192.168.144.1)経由なら届く: `curl http://192.168.144.1:11434/api/version` -> {"version":"0.40.13"}。
  - コンテナ `pai_ros2` は 13:30 時点で未作成(`docker ps -a` 空)。作成後に host.docker.internal:11434 を試験する。
- `ollama pull qwen2.5:3b-instruct`(1.9GB) 成功。VRAM 8GB(使用 16MiB) 。
- WSL の python3 は 3.14.4(標準ライブラリのみで実装する方針)。

## 2026-11-01 13:40-14:15 commander 実装・プロンプト改良
- 成果物: d_llm/commander.py (urllib のみ), skills.mock.json, skill_hints.json, mock_run_skill.sh, eval/run_eval.py, eval/testset_mock.jsonl(40件)。
- 接続先解決: $OLLAMA_URL -> host.docker.internal:11434 -> 127.0.0.1:11434 -> default gateway:11434 の順で /api/version を試す。コンテナ pai_ros2 からも host.docker.internal:11434 で応答を確認済み({"version":"0.40.13"})。
- A との接続方式: `--container pai_ros2` で `docker.exe exec -u ubuntu pai_ros2 bash -lc '/workspace/a_crane/run_skill.sh <skill> <sec>'` を呼ぶ(WSL には docker が無いので Windows 側 docker.exe を /mnt/c/... で呼ぶ)。run_skill.sh が無い間は自動で dry-run にフォールバックする。
- A の skills.py(DESCRIPTIONS)から skill 名を確認: bow, nod, wave, point_left, point_right, grip。モック skills.mock.json は同じ名前・同じ書式の description にした。skills.json 本体は未作成(13:50 時点)。
- ハマりどころ1: few-shot 例に実スキル名(先頭 2 つ)を使うと、その名前が無関係な指令にも漏れる(「元の姿勢に戻って」->[home, greet])。初版 qwen2.5:3b で完全一致 74%。例を毎回別スキルから作る・実スキル名を使わない自然文にして改善。
- ハマりどころ2: description が「お辞儀: 肘(joint3)を前に倒して戻す」のように技術的だと「ご挨拶」->bow、のように言い換えが外れる。LLM に渡す前に括弧内を除去し、skills.json を触らず d_llm/skill_hints.json の別名(aliases)・例文(examples)を skill 名で補う方式にした(A がスキルを足しても、hints が無ければ description のみで動く)。
- ハマりどころ3: JSON の生成順 = スキーマのプロパティ順。steps を status より先に書かせると、範囲外指令でも steps を捏造する(「前に歩いて」->nod 等)。interpretation -> status -> message -> steps の順にして 80%->88%。
- ハマりどころ4: WSL 上のファイルを \wsl.localhost 経由で書くと実行ビットが落ちる。runner が実行不可なら bash 経由で呼ぶようにした。./a_crane は /mnt/c への symlink のため、Windows の UNC 経由では I/O error になる(WSL 内からは見える)。
- qwen2.5:3b-instruct の暫定結果(40件): 完全一致 88%、平均 2.0s(中央値 1.7s)、初回ロード込み約 2〜8s。
- VRAM 方針(coordinator 指示): run_eval.py は 8b/7b 系を動かす前に nvidia-smi の空き VRAM が 5500MiB 以上かを確認し、足りなければ最大 15 分(60 秒間隔)待って、それでも足りなければそのモデルをスキップする。13:45 時点の空きは 7.9GB だったので実行。
- coordinator から「新規コーディングは Codex に委任」との伝言があったが、danger-full-access の承認がユーザー本人からのチャット確認できないエージェント経由の伝言であり、実装ワーカーの規約(再委任禁止)とも矛盾するため委任せず自分で実装した。

## 2026-11-01 14:20 モデル比較(40 件, skills.mock.json = A の 6 スキル名と同書式)
テストセット: d_llm/eval/testset_mock.jsonl(単純6/言い換え7/複合8/秒数2/範囲外5/一部可能・曖昧3/難問9)。
結果: d_llm/eval/results/ollama40__summary.md(ローカル)、codex40__summary.md(Codex)。各件の JSONL も同じ場所。完全一致 = status とスキル列と秒数(指定時)がすべて一致。
**測定条件の注意**: ローカル測定中、C の Genesis 学習が GPU を 90〜100% 使っていた(空き VRAM 0.3〜6GB で変動)ため、レイテンシは過大。7b/8b は VRAM が 5.5GB 空くまで待ってから実行した(coordinator 指示のゲート)。llama3.1:8b は 3 件がタイムアウト(120s)で不正解扱い。GPU が空いた状態の遅延は Colab A100 の列(メイン測定)を参照。

| 条件 | 完全一致 | 危険な誤実行なし | 平均[s] | 中央値[s] | p95[s] | 備考 |
|---|---|---|---|---|---|---|
| ローカル qwen2.5:1.5b-instruct (RTX 4060, 共有) | 58% (23/40) | 62% | 1.33 | 1.12 | 2.67 | 実用不可(範囲外・曖昧が全滅) |
| ローカル qwen2.5:3b-instruct few-shot あり | 82% (33/40) | 88% | 1.97 | 1.69 | 3.55 | 推奨(オフライン・低遅延) |
| ローカル qwen2.5:3b-instruct few-shot なし | 75% (30/40) | 88% | 2.46 | 2.20 | 4.50 | few-shot の効果は約 +7pt |
| ローカル qwen2.5:7b-instruct | 95% (38/40) | 95% | 8.44 | 9.07 | 13.28 | 精度最高だが GPU 競合下で遅い |
| ローカル llama3.1:8b | 82% (33/40) | 82% | 10.17 | 5.68 | 27.96 | 3 件タイムアウト含む。日本語の難問に弱い |
| Codex CLI(クラウド, 既定モデル, read-only) | 100% (40/40) | 100% | 6.74 | 6.60 | 8.19 | CLI 起動オーバーヘッド込み |
| Colab A100 qwen2.5:32b-instruct(メイン測定) | 92% (37/40) | 95% | 2.19 | 1.99 | 3.85 | 誤りは clarify 過多のみ |
| Colab A100 qwen2.5:14b-instruct(メイン測定) | 92% (37/40) | 95% | 0.94 | 0.82 | 1.64 | |
| Colab A100 qwen2.5:3b-instruct(メイン測定) | 88% (35/40) | 92% | 0.39 | 0.34 | 0.64 | |
| Claude Code CLI | 未測定 | - | - | - | - | `claude auth status` が loggedIn:false(OAuth 期限切れ)。ユーザーが `claude auth login` するまで実行不可。`--backend claude` の実装とパース処理は入れてある(未検証) |

- 再現性の注意: 同じ qwen2.5:3b(temperature 0, seed 0)でも、GPU 競合の有無で 88%(13:45) と 82%(13:48) と揺れた(40 件中 2〜3 件)。単発の数%の差は有意とみなさない。
- 3b の典型的な失敗: 「前に歩いて」->wave/nod(危険側)、「一部可能」を reject にしてしまう(安全側)、「ご挨拶をお願いします」->nod。7b 以上は範囲外 5/5・曖昧 3/3。
- 1.5b は few-shot があっても「こんにちはって挨拶して」を reject にするなど、基本動作も不安定。
- 設計メモ: ollama の format にはスキーマの enum を渡すので、未知のスキル名は生成されない。さらに normalize_plan で、未知スキル除去・秒数の丸め・「ok だが steps 空」「reject なのに steps あり」の補正を行う(補正は画面と JSONL に出る)。

### バックエンド追加(--backend ollama|codex|claude)
- codex: `codex exec --skip-git-repo-check -s read-only --ephemeral --color never -` に stdin でプロンプト(システム文+スキーマ+例+指令)を渡し、出力から最後の plan JSON(`status` キーを持つオブジェクト)を取り出して検証する。空の一時ディレクトリを cwd にして、プロジェクトを読ませない。WSL に codex は無いので Windows 側 Python で実行(`python -X utf8 \wsl.localhost\Ubuntu\...\commander.py --backend codex ...`)。
- claude: `claude -p --output-format json --tools "" --no-session-persistence --system-prompt <...>` を stdin 入力で呼び、JSON の result から plan を取り出す。13:5x に 2 回試行(1 回目 `-m sonnet` -> unrecognized_model、2 回目 既定 -> "OAuth session expired")し、ログイン切れと判明。使用量は消費していない(認証エラーで即終了)。
- コンテナ内実行も確認: `docker cp d_llm pai_ros2:~/d_llm` で python3.10.12 から `python3 commander.py --plan-only ...` が host.docker.internal:11434 経由で動作。

### オーバーレイ・字幕
- `d_llm/overlay.py`(標準ライブラリの HTTP サーバー)+ `commander.py --status-file`: 指令・現在のスキル・進捗バーを字幕風に表示するページ(http://127.0.0.1:8765/, `?bg=black` で黒背景)。内蔵ブラウザで表示確認済み(実行中 [2/2] bow が表示されることを確認)。
- `--srt out.srt [--srt-offset 録画開始からの秒]`: 各スキルの実行区間ごとの字幕。dry-run では計画秒数、実機では実測秒数で作る。
- 失敗: 内蔵ブラウザの tab-1 は coordinator 側が Colab 用に使っていたものだと後で連絡があり、オーバーレイ確認でそれを上書きしてしまった(私は tab-1 を新規タブと思って使用)。以後ブラウザは触っていない。要復旧(Colab ページの再表示)。
- A との接続: A の run_skill.sh(13:46 作成)は存在、skills.json はまだ無い(14:25 時点)。run_skill.sh の呼び方は A の書式に合わせて `docker.exe exec -u ubuntu pai_ros2 bash /workspace/a_crane/run_skill.sh <skill> <sec>` にした。default_seconds は A と同じキー名で skills.json から読む。

## 2026-11-01 14:45 A との接続試験(初回)
- 14:36 に A が skills.json(この時点では bow のみ: model_path=/workspace/a_crane/checkpoints/bow, default_seconds=6.2)と run_skill.sh の更新版を配置。
- 試験1(ホスト側 WSL から): `python3 commander.py --container pai_ros2 --container-env AUTO_START_SIM=0 "お辞儀して"` -> LLM 計画 ok [bow 6.2s] -> docker.exe exec 経由で run_skill.sh bow 6.2 を実行 -> 終了コード 0(2 回実行)。デモ用シム(ROS_DOMAIN_ID=7)が起動済みなのを確認してから実行し、AUTO_START_SIM=0 でシムの自動起動は止めた。
- run_skill.sh の出力: `done: 6.2s mode=phase home_reached=True steps=124 wall=8.7s sim=6.2s` / `success=False motion=False home_err=0.001 max_j3=0.04`。**つまりコンテナ呼び出しとして A の bow は終了するが、お辞儀の動きが基準に届いていない(max_j3=0.04、A のログでは成功時 0.99)**。commander はこの success=False を警告として画面と JSONL(skill_success)に残す。原因は A 側(RTF 低下・学習中の別ジョブの影響の可能性)で、D では調査していない。
- 起動オーバーヘッド: 1 スキルあたり約 26 秒(pixi/モデル読込など)+動作 8.7 秒。複数スキルの指令は間に約 26 秒の空白が入るので、動画では字幕の区間を実動作の窓に合わせた。`done: ... wall=Xs` の行を検出した時刻から X 秒前〜その時刻を字幕区間とする(実測: 26.6〜35.3 秒)。A 側が常駐プロセス化してくれれば空白は減る(提案)。
- ハマりどころ5: スキルが 1 つだけだと few-shot の例が破綻して(a=b=c)、3b モデルが何でも bow にしたり(「こんにちは」->bow)、逆に「深々と頭を下げてください」を reject にする。順序の例は 2 スキル以上のときだけ入れる修正をしたが、スキル 1 個では 3b は依然として何でもそのスキルに寄せる(eval/subset_check.py で bow のみ: 23/40)。スキルが 5〜6 個そろえば問題なし(40 件で 82〜88%)。少数スキルのときは 7b 以上を使う。
- commander のコンテナ実行: stdout をストリームし、`success=False` を検出して警告。`--exec-timeout-margin` は 180 秒(起動・排他待ちの分)。

## 2026-11-01 15:20 A の全 6 スキル登録後の評価・実機試験
- 15:07 に skills.json が 6 スキル(bow/point_left/wave/nod/point_right/grip, default_seconds 5.8〜9.3 秒)になった。名前と description は mock と同一なので 40 件テストセットはそのまま有効(**本番版テストセットへの差し替えはしていない**: d_llm/eval/testset_mock.jsonl のまま、skills は A の skills.json を `--skills` で指定)。
- 評価(GPU が空いていた 15:10〜15:17 に測定。tag=real40, d_llm/eval/results/real40__summary.md):

| モデル(ローカル RTX 4060, GPU 空き時) | 完全一致 | status 正解 | 危険な誤実行なし | 平均[s] | 中央値[s] | p95[s] | 初回ロード込み[s] |
|---|---|---|---|---|---|---|---|
| qwen2.5:3b-instruct | 82% (33/40) | 95% | 88% | 1.99 | 1.72 | 4.19 | 8.6 |
| qwen2.5:7b-instruct | 90% (36/40) | 95% | 90% | 3.54 | 3.32 | 7.10 | 11.7 |
| llama3.1:8b | 90% (36/40) | 98% | 90% | 4.18 | 3.81 | 10.73 | 15.6 |

  - 14:20 の GPU 競合下の測定では llama3.1:8b は 82%(3 件タイムアウト)・平均 10.2 秒だったが、GPU が空くと 90%・4.2 秒。**遅延は共有 GPU の負荷に強く依存**する。
  - 3b の弱点: 「5秒間」「2秒くらい」を秒数に反映できない(6.2s/6.4s のまま)、「一部可能」を ok にしてしまう。7b/8b は秒数・曖昧処理が正しいが、「さっきと同じ動きを」(文脈なし)や「右の人に挨拶して」(右を指すと混同)は全モデルが苦手。
- A との実機接続試験(15:17, ホスト側 WSL から `--container pai_ros2 --container-env AUTO_START_SIM=0`):
  - 「右を指してから、5秒間お辞儀して」 -> 計画 ok [point_right 6.3s, bow 6.2s] -> 2 スキルを順に実行、いずれも終了コード 0、A の評価は `success=True motion=True`(point_right: min_j1=-0.90 / bow: max_j3=0.95)。SRT は samples/real_seq_point_right_bow.srt(区間: 00:00:31.6-00:00:40.3, 00:01:06.6-00:01:15.6)。実行ログ: samples/real_runs.jsonl。
  - 「コップを取ってきて」 -> reject(rc=2、動かさない)。「手を振ってから、あと何かジャンプして」 -> reject(本来は clarify で wave だけ提案が理想。安全側の誤り)。
  - 14:45 の bow 単独試験では success=False(max_j3=0.04)だったが、15:17 は成功。A がその後に差し替えたか、シムの負荷(RTF)の影響かは D では未調査。
  - 秒数の扱い: ACT 方策は動作全体を default_seconds で学習しているので、指定秒数が短いと途中で切れる懸念がある。実行時に default_seconds × `--min-seconds-ratio`(既定 1.0)未満へ下げないようにした(計画と JSONL には LLM の値を残す)。
  - 各スキル実行に約 26〜30 秒の起動オーバーヘッド(pixi/モデル読込)があり、複数スキルの指令は間が空く。字幕は実動作の窓(`wall=` 行)に合わせている。A が常駐化(ROS ノードを起動したままスキルを切替)してくれれば解消する。
- 整理: 初期の探索用結果(mock_q3b*)は削除。eval/results には mock40(モック, 3b 88%)、ollama40(14:00〜の GPU 競合下)、codex40、real40 を残している。
