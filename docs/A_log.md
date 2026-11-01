# ストリームA 作業ログ（CRANE+ V2 / Gazebo / ACT）

## 2026-11-01 13:27 開始
- 環境確認: WSL Ubuntu 内に `docker` コマンドが無い（Docker Desktop の WSL integration が Ubuntu で無効）。Windows 側の docker.exe は動作。
- `-v \wsl.localhost\Ubuntu\...` でのマウントは `distro mount service ... ubuntu.sock: no such file` で失敗（integration 無効のため）。
- 判断: Docker Desktop の設定は変更せず、Windows 側 `./{a_crane,docs}` をコンテナの `/workspace/{a_crane,docs}` にマウント。
  WSL 側は `./a_crane -> ./a_crane`、`docs/A_log.md -> ./docs/A_log.md` のシンボリックリンクで同じ実体を参照。
- コンテナ作成（PowerShell から）:
  `docker run -d --name pai_ros2 --gpus all -p 6080:80 -p 9090:9090 -p 9876:9876 --shm-size=1g --memory=3.5g -v ./a_crane:/workspace/a_crane -v ./docs:/workspace/docs airobotbook/ros2-desktop-ai-robot-book-humble:latest`
  - `--memory=3.5g` は RAM 共有のため追加。GPU 認識 OK（RTX 4060 Laptop）。VNC の DISPLAY は `:0`。
  - 注意: コンテナ内では Windows ファイルシステム越しの I/O が遅いので、bag・データセット・学習出力はコンテナ内 `~/` に置き、成果物（コード・最終チェックポイント・動画）だけ `/workspace/a_crane` へコピーする方針。

## 13:30–13:37 セットアップ
- `git clone --recursive pai_training`、pixi install（約5分、glibc の WARN のみで成功）。`~/pai_ws/src/physicalai_teleop` を clone して colcon build（5.6秒）。
- crane_plus 系パッケージはイメージの `~/airobot_ws` にビルド済み。
- `a_crane/launch/sim.launch.py` を作った（no_moveit 版がベース。`gui:=false` で `ign gazebo -s` のヘッドレス起動ができる）。起動・停止は `a_crane/scripts/sim_ctl.sh start [true|false] / stop`。
- **ハマりどころ1**: `/joint_states` の並びは joint1, joint2, **joint4, joint3**。teleop の指令も同じ並び（講義の infer.py もこの並び）。自作ノードは内部で意味どおりの並び [j1,j2,j3,j4] を使い、publish する直前に並べ替える。
- **ハマりどころ2**: RTF は GUI ありで約 0.83、ヘッドレスで約 0.92（`scripts/rtf.sh`）。指令に対して実際の関節は 0.3〜0.5 秒遅れて追従する（遅い）。そのためスキルの所要時間を 1.3〜1.9 倍に伸ばした。
- **ハマりどころ3**: `ros2 bag record` の起動には1秒以上かかり、最初の試行では動作の冒頭が記録されなかった。db3 ファイルができるのを待ってから 0.7 秒の余裕をとる方式にした。終了時は直立姿勢に戻ったこと（誤差 0.03 rad 未満）を確認してから 0.5 秒後に記録を止める。
- 13:37 bow の自動収集を 50 エピソード開始（ヘッドレス、seed 0）。ベースラインには ep 0〜19 を使い、データ数の比較には 10/30/50 を使う予定。
- 方針メモ: 途中でコーディネータから「Codex（danger-full-access）に委任せよ」という指示が来たが、このワーカーの定義（再委任の禁止）と、エージェント経由の承認は採用しない原則に従い、委任せず自分で実装を続けた。

## 13:37–13:50 ベースライン（講義の手順どおり）とパイプライン整備
- bow 50 エピソードを自動収集（1 エピソード約 13 秒。記録の起動待ちと直立姿勢への復帰待ちを含む）。
- ベースライン = **講義の公式コマンド**: `configs/conversion_config.yaml` の bag_dir を `~/dataset/rosbags/bow_baseline20`（ep 0〜19 のコピー）に変更して `pixi run convert`（25 秒、20 ep / 2640 フレーム）。
  `configs/train_config.yaml` は device=cuda、batch 32、3000 ステップ、delta_timestamps.action=[0.0 … 1.5]（16 個）、n_action_steps=1 にして `WANDB_MODE=offline pixi run train`。元の設定ファイルは `*.orig` として残した。
- **ハマりどころ4**: 講義の train.py は DataLoader（num_workers=2）がエポックごとにワーカーを作り直す。データが小さい（約80バッチ/エポック）ので、その都度プロセス生成（1プロセス約1GB RSS）が起き、100 ステップに約 25 秒かかった。
  → 自作の `a_crane/scripts/train_act.py` では、全サンプルを一度だけ読み込んで GPU 上のテンソルにキャッシュし、そこからランダムにバッチを取る方式にした（キャッシュに約 160 秒、学習は約 7 ステップ/秒）。
- **ハマりどころ5**: Windows 側で書いたスクリプトに CRLF が混ざり、bash が `$'in\r'` エラーを出した。sed で LF に統一した。
- 2 つのシミュレーションを並行して動かせるようにした: `SIM=collect`（ROS_DOMAIN_ID=0、ヘッドレス、収集用）と `SIM=demo`（ROS_DOMAIN_ID=7、IGN_PARTITION=demo、GUI、推論と録画用）。ただしメモリの上限（3.5GB）が厳しいので、GUI 版は使うときだけ起動する。
- **拡張（工夫）: 位相つき観測 `env-mode=phase`**。講義の設定では observation.environment_state = state で、観測が関節角だけになる。
  そのため「倒していく途中と戻る途中で同じ角度」「開始時と終了時の直立」が区別できない（多峰性）。
  そこで environment_state = [エピソード開始からの経過秒数 t, 直近 0.1 秒の各関節の変位 dq1..dq4] とした（`scripts/convert_ext.py`、推論側は `scripts/skill_runner.py`）。

## 13:55–14:10 ベースラインの評価と、位相つき観測の手直し
- ベースラインの学習（公式 `pixi run train`、3000 ステップ、batch 32、GPU）: 約 14 分で、最終 loss は 0.082。
- **debug-policy（公式、ep1/ep5）**: GT との平均 L2 誤差は 0.0546 / 0.0562。図は `a_crane/results/debug_baseline_ep{1,5}.png`。
  戻りの区間で予測が GT より上（まだ下げる側）に外れていて、状態だけの観測では「行き／帰り」の区別がつかないことが図からも分かる。
  （debug_policy.py は plt.show() で止まるので、`scripts/debug_policy_save.py` で PNG に保存するラッパを作った）
- **Gazebo 上での推論（ベースライン）**: 公式の `pixi run infer` が動くことを確認した。評価には同等の `skill_runner.py --env-mode state` を使う。
  12 秒走らせると j3 が 0 → 0.35 までじわじわ上がるだけで、戻ってこない（失敗。max_j3=0.35 < 0.4、終了時の誤差 0.35）。
  静止している状態から「少しだけ先」を出し続ける、いわゆる追従（copycat）のような挙動になった。
- **バグ**: skill_runner の周期待ちで、推論が 50ms を超えると spin_once が呼ばれず、/joint_states が更新されなかった。毎周期必ず spin_once(0) を呼ぶように直した。推論は GPU 既定にした。
- **位相つき観測の初版 (t, dq)** は失敗した: 動き出した直後に dq≈0 のまま止まってしまう。dq（速度の代わり）に頼る copycat 問題（因果の混同）と判断した。
  → **最終版の phase = [t, 0, 0, 0, 0]（時刻だけ）** にし、さらに各エピソードを「指令が動き出す 0.25 秒前」から切り出して、時刻の原点をそろえた（`--lead 0.25`）。初版は `phasedq` として残してある。
- 学習の高速化: キャッシュ作成を `ds[i]` の繰り返しから parquet の列から直接作る方式に変えた（160 秒 → 1 秒）。`--check` で LeRobotDataset[i] と一致することを確認した。

## 14:10–14:20 収集の完了と学習の作り直し
- 自動収集の結果: bow 50 / point_left 40 / wave 40 / nod 40 / point_right 40 / grip 40 = **250 エピソード、約 40 分（13:37〜14:17）**。
  250 エピソードすべてで開始時に直立姿勢を確認でき（home_ok_before=True）、終了時の誤差は最大でも 0.036 rad。人手によるテレオペは 0 回。
- **ハマりどころ6**: GPU は他のストリーム（Genesis）と共有しているため使用率がほぼ 100%（全体で 7.6GB 使用）で、ACT の既定サイズ（約 5200 万パラメータ）は約 1.3 ステップ/秒しか出なかった。
  → 入力が 5 次元しかないので、ACT を小さくした（dim_model 256、FFN 1024、encoder 2 層、VAE encoder 2 層。`train_act.py --model-size small`）。
  GPU の列（本番の 6 スキル、各 2500 ステップ）と CPU の列（bow の 10 / 30 / 50 エピソードの比較、state 観測との比較）を並行して流す（`scripts/queue_gpu.sh`、`scripts/queue_cpu.sh`）。
- **ハマりどころ7**: コンテナ内で `pkill -f train_act.py` を `bash -c` の中から実行すると、自分のシェル自身（コマンド行にその文字列を含む）まで殺してしまう。PID を指定して止めるべき。
- 収集用シム（domain 0）は停止した。

## 14:20–14:35 最大のハマりどころ: 実時間比（RTF）の違いでモデルが移植できない → シミュレーション時刻にそろえる
- 位相つきの bow モデル（50 ep）を GUI 版のシムで動かしても、動き出してすぐ止まり、失敗した（max_j3=0.05）。
- 原因の調査: 同じシムでスクリプトによる bow を流しても、指令 0.73 に対して関節は 0.40 までしか届かない（収集時は 0.66）。
  学習（CPU 側で torch が全コアを使用）と GUI の描画で RTF が 0.92 → 0.56 に落ち、**壁時計で見たロボットの応答が約 2 倍遅くなっていた**。
  講義の変換器は bag の受信時刻（壁時計）で 20Hz にリサンプルし、推論も壁時計の 20Hz で回すので、RTF が変わると時間スケールがずれる。
- **対策（工夫2）: 時間の基準をすべてシミュレーション時刻にした**
  - 変換（`convert_ext.py --clock sim`、既定）: /joint_states の header.stamp（シム時刻）を時間軸にする。stamp を持たない指令トピックは、「受信時刻（壁時計）→ シム時刻」の対応を補間して変換し、そのうえで 20Hz にリサンプルする。
  - 推論（`skill_runner.py`）: use_sim_time=True で /clock を購読し、**シム時刻の 0.05 秒ごと**に 1 回だけ推論・publish する。
- 結果: 同じ bow の 50 ep を作り直して再学習（2500 ステップ、124 秒）すると、**GUI 版のシム（RTF 約 0.6）で成功**した（max_j3=0.99、終了時の誤差 0.002、シム 8 秒 ≒ 壁時計 9.8 秒）。
- その他: CPU で学習するときは torch のスレッド数を 4 に制限した（`TORCH_THREADS`）。CPU 学習を一時停止するための `scripts/cpu_jobs.sh pause|resume` も作った。全モデルは GPU で順に学習する方針に変更した（小型 ACT で 1 モデル約 2.5 分）。

## 14:35–15:13 安定化（3つのバグ／弱点を修正）と、最初の推論録画
1. **正規化の std がほぼ 0**: bow では j1/j2/j4 がほとんど動かず、state の std が 0〜0.002 になる。LeRobot は (x-mean)/(std+1e-8) で正規化するため、Gazebo で 0.001 rad 揺れただけで数百〜数百万σの入力になる。
   状態に加えたノイズ（σ=0.02）がこれで発散し、時刻を無視して定数を出すモデルになった（`scripts/probe_policy.py` で開ループに入力して発見）。→ state と action の std を 0.05 rad 以上にクランプした（`--min-std 0.05`）。状態ノイズは既定で 0 にした。
2. **遅れの水増し（lag augmentation、工夫3）**: 学習時に、観測する状態を 0〜8 フレーム（最大 0.4 秒）前のものに置き換える。目標の行動はそのまま。シムの応答が収集時より遅くても、方策がスキルの時間軸に沿って進み続けるようにするため。
3. **/clock の取りこぼし**: 推論ループで spin_once を 1 回ずつ呼んでいたため、約 1kHz の /clock が溜まり、ノードの時計が最大 2.3 秒遅れて飛んだ。→ executor をバックグラウンドのスレッドで回す方式に変えた。最初の推論が遅い問題には、ウォームアップ（3 回推論）と実経過シム時刻 t の使用で対処した。
- 結果: bow（50 ep）は **5/5 成功**、さらに 3/3。point_left（40 ep）は **5/5 成功**（max_j1≈0.87、max_j2≈0.91、終了時の誤差 0.010）。
- 録画: `scripts/demo_record.sh <skill>` → `a_crane/videos/bow_055933.mp4`、`point_left_060012.mp4`（各約 15 秒、1184x928、左上にラベル）。
  - ハマりどころ: VNC デスクトップの **MATE スクリーンセーバー（floaters）** が数分の放置で起動し、画面上を MATE のロゴが漂って映り込む。session の DBUS を拾って gsettings で無効にした（コンテナ内のデスクトップ設定のみ。`gazebo_window.sh` で毎回設定する）。
  - カメラは ign service `/gui/move_to/pose` で (0.42,-0.42,1.36) から腕を見下ろす位置に置く。録画の開始は skill_runner が作る START_MARKER ファイルで合わせる（pixi の起動待ちを映さないため）。
- `run_skill.sh <skill> [seconds]` と `skills.json` は動作確認済み（bow、point_left を登録）。

## 15:13–15:25 残りのスキルの評価と録画
- point_right（40 ep）**5/5**、grip（40 ep）**5/5**（グリッパを閉じ 0.18、終了時に開いて -0.53）。録画: `videos/point_right_060604.mp4`、`videos/grip_060906.mp4`。
- wave（40 ep）**0/3**、nod（40 ep）**0/3**: 周期的なスキルでは腕の振れが小さくなる（wave の j1 は [-0.12, 0.27]、nod は 1 回）。
  - debug-policy（`results/debug_wave_n40_phase_ep1.png`、L2=0.26。bow は 0.054、point_left は 0.074、grip は 0.089）では、GT の状態を与えても予測の振動の**位相がずれている**。
  - 原因の見立て: 収集時にテンポ（所要時間の倍率 s）を 1.3〜1.9 の範囲でランダムにしたため、k 回目の振りが起きる時刻がデモごとに大きく異なる。時刻 t を条件にした方策は、それらを平均して振幅の小さい線にしてしまう（時間方向の多峰性）。
  - 対策: wave と nod だけ**テンポをほぼ固定**（s=1.55〜1.65、振幅はランダムのまま）にして 40 ep ずつ収集し直す（`FIXED_TEMPO=1 TAG=_v2 collect.sh`、15:16 開始）。
- （D からの照会に回答）14:45 に D が実行した bow が失敗した（max_j3=0.04）のは、当時の skill_runner の **/clock 取りこぼしのバグ**のため（ループ内で spin_once を 1 回ずつ呼んでいたので、ノードのシム時計が最大 2.3 秒遅れて飛び、時刻入力 t が狂った）。14:55 に executor をバックグラウンドのスレッドで回す方式に直し、それ以降は bow 13/13 成功。
- D の計測: run_skill.sh 1 回あたり、動き始めるまでに 26〜30 秒かかる（pixi の起動、torch/lerobot の import、モデルの読み込み、ウォームアップ）。常駐モードは時間に余裕があれば実装する。

## 15:25–15:45 アブレーション、講義版 infer との比較、常駐サーバ
- **講義の infer.py（無改変）＋ベースラインのモデル**: `scripts/eval_lecture_infer.sh` で 3 試行 → **0/3**。1 回目は 0.36 までじわじわ上がるだけ、2〜3 回目は 0.74〜0.76 まで下げたあと戻らない。
  （壁時計 20Hz のタイマー、CPU での推論。終了時に segfault するが評価には影響しない）
- **同じベースラインのモデルを自作の skill_runner（シム時刻の 20Hz、GPU、ウォームアップ、バックグラウンド spin）で動かす**と **5/5**（max_j3 0.94〜1.01）。
  → 13:55 にベースラインが失敗した主因は、モデルよりも実行系（実時間比と spin のバグ）にあった。報告書では「実行系の改善だけで 0/3 → 5/5」と書く。
- bow_n50_state（観測は state のみ、エピソードの冒頭を切り詰め、遅れの水増しあり）は **0/5**（動き出さない）。
  データを切り詰めたので「冒頭の直立」は 5 フレームしかなく、末尾の「直立で静止」が大部分を占める。状態だけ見ると直立 → 静止、と学習してしまう（開始と終了の多峰性がそのまま出た例）。phase 観測では同じデータで 5/5。
- データ数（bow、phase 観測）: n10 **5/5**、n30 **5/5**、n50 **5/5**。bow は易しく、10 エピソードで飽和する。
- **常駐モード**（D の提案に対応）: `scripts/skill_server.py`（全モデルを GPU に常駐させ、ウォームアップ済み。127.0.0.1:9877 で JSON を 1 行受け取る）と、`scripts/skill_client.py`。
  `run_skill.sh` は、サーバが動いていればクライアントとして要求を送り（終了コード 0/1）、動いていなければ従来どおり新しいプロセスで実行する。
  起動: `docker exec -u ubuntu pai_ros2 bash /workspace/a_crane/scripts/skill_server.sh start`。
  計測: bow（シム 6.2 秒）の呼び出し全体が **10.6 秒**（RTF 約 0.65 なので、動作そのものが約 9.5 秒）。待ち時間は 26〜30 秒から約 1 秒になった。grip は 13.9 秒。
- skills.json には、現時点で成功している bow / point_left / point_right / grip だけを登録している（wave と nod は作り直し中）。

## 15:45–16:00 周期スキル（wave / nod）の作り直し
- v2（テンポを壁時計で固定）: wave **0/3**。debug-policy の L2 は 0.27 のまま。シム時刻に直したエピソード長が 101〜144 フレームとばらつく。
  → 収集時の RTF が 0.6〜0.9 で変動するので、**壁時計で固定したテンポはシム時刻では固定にならない**。
- v3: **自動デモの軌道そのものもシム時刻で 0.05 秒ずつ進める**ようにした（`auto_demo.py` に `SIM_TIME=1`）。テンポはほぼ固定（s=1.55〜1.65）。wave / nod を 40 ep ずつ収集した（各約 20 分）。
  - wave n20 v3: オフラインの L2 は **0.27 → 0.11**（`results/debug_wave_n20_phase_v3_ep1.png`）。ただし閉ループでは **0/3**: 開始時に j1 がわずかに負へずれ、方策がそれを「負側へ振っている途中」と解釈して位相がずれる（状態への依存）。
  - 状態ノイズ σ=0.1 / 遅れ 12 では、1 回目の振りは出るが 2 回目が出ない（0/3）。σ=0.3 / 遅れ 16 では振幅が縮んだ（0/3）。
  - **工夫4: チャンクの開ループ実行（chunk_exec）**: 予測したチャンク（0.1 秒刻み）のうち先頭 8 個（0.8 秒分）を、閉ループに戻さずにそのまま実行する（`skill_runner.py --chunk-exec 8`、2 tick ごとに次の要素を出す）。
    → wave n20 v3 は chunk 8 で **2/2**、chunk 16 で **2/2**。**wave n40 v3 は chunk 8 で 5/5**（j1 が [-0.42, 0.49] を 2 往復）。
- **評価基準の見直し**: `scripts/eval_demos.py` で、**成功条件をデモ自身にも当てはめて**検証した。
  bow 40/40、point_left 39/40、point_right 40/40、grip 40/40、wave v3 34/40、nod v3 39/40（いずれも当初の条件。ただし nod の条件のみ下記のように見直した）。
  一方 **v1 のデモは wave 7/40、nod 10/40**: テンポが速いと、遅いサーボが追従できず、デモ自体の振幅が出ていなかった（v1 が失敗した原因の一つ）。
  nod の谷の閾値 0.05 は、デモ自身の谷（約 0.07）でも満たせなかったので 0.15 に変更した（山 0.25 / 谷 0.15）。v1 の nod の記録を新しい基準で評価し直しても 0/3 のまま。
- nod n40 v3（chunk 8）: **5/5**（2 回うなずく）。
- skills.json に wave（v3、chunk_exec=8）と nod（v3、chunk_exec=8）を追加し、**6 スキルすべてを登録**した。常駐サーバは a_crane_meta.json の chunk_exec を読む。
- 録画: `videos/wave_065523.mp4`、`videos/nod_065537.mp4`。比較用: `videos/baseline_lecture_infer_062712.mp4`（講義の infer.py ではうまく動かない）、`videos/baseline_model_improved_runner_062804.mp4`（同じモデルを改良版の実行系で動かすと成功）。
  - 注意: 常駐サーバを kill -9 で止めた直後に再起動すると、/joint_states を受け取れない状態になることがあった。`skill_server.sh stop`（TERM のあと KILL）で止めてから起動し直すと直った。リクエスト時に最大 5 秒待つ処理も追加した。

## 16:00–16:10 結果のまとめ（`a_crane/results/summary.csv`）
### Gazebo 上での成功率（成功の条件は `scripts/eval_traj.py`。特徴的な動作が出て、方策の実行の終わりに直立姿勢から 0.15 rad 以内に戻っていること）
| 条件 | スキル | デモ数 | 成功 |
|---|---|---|---|
| 講義のパイプラインのまま（train.py + infer.py） | bow | 20 | **0/3** |
| 同じモデル + 改良した実行系（シム時刻 20Hz） | bow | 20 | **5/5** |
| state 観測（切り詰め + 遅れの水増し） | bow | 50 | 0/5 |
| **最終: phase 観測 + シム時刻 + 遅れの水増し + std クランプ** | bow | 50 | **5/5** |
| 〃 | point_left | 40 | **5/5** |
| 〃 | point_right | 40 | **5/5** |
| 〃 | grip | 40 | **5/5** |
| 〃 + テンポ固定（シム時刻）+ チャンクの開ループ実行 8 | wave | 40 | **5/5** |
| 〃 | nod | 40 | **5/5** |
| v1（テンポをランダム化）| wave / nod | 40 | 0/3 / 0/3 |
| v3 の閉ループ（chunk_exec=1） | wave | 20 | 0/3 |

### データ数との比較
| スキル | 10 | 20 | 30 | 40 | 50 |
|---|---|---|---|---|---|
| bow（易しい） | 5/5 | – | 5/5 | – | 5/5 |
| wave（周期、chunk 8） | 4/5 | 5/5 | – | 5/5 | – |

### debug-policy（GT との比較。学習に使ったエピソード ep1 の平均 L2）
ベースライン 0.055 / bow 0.054 / point_left 0.074 / point_right 0.105 / grip 0.089 / wave v1 0.264 → v2 0.271 → v3(n20) 0.108 / wave v3(n40) 0.198 / nod v3 0.191。
図は `a_crane/results/debug_*.png`。

### 録画
- 各スキル: `videos/{bow_055933, point_left_060012, point_right_060604, grip_060906, wave_065523, nod_065537}.mp4`
- 比較: `videos/baseline_lecture_infer_062712.mp4`、`videos/baseline_model_improved_runner_062804.mp4`
- **まとめ動画（126.7 秒）**: `videos/montage_a_crane.mp4`（タイトルカード → ベースライン 2 本 → 6 スキル。`scripts/make_montage.sh`）

### 注意（レポートでは限界として書く）
- 試行ごとの差は、シムがほぼ決定論的なので小さい。成功率は 5 試行で、初期姿勢は毎回同じ。外乱や初期姿勢のばらつきに対する頑健性は評価していない。
- nod の成功条件は、デモを見たあとで変更した（谷の閾値 0.05 → 0.15）。v1 の nod は、新しい基準で評価し直しても 0/3。
- wave は今のカメラの角度だと動きが分かりにくい（旋回軸の回転なので）。

## 16:05–16:15 頑健性（初期姿勢をずらす）と仕上げ
- `skill_runner.py --start-pose`（開始姿勢を指定）を追加した。各 3 試行:
| スキル | j1+0.25 から開始 | j2,j3,j4 を +0.2 から開始 |
|---|---|---|
| bow | 3/3 | **0/3**（直立には戻るがお辞儀をしない。max_j3=0.20） |
| point_left | 3/3 | 3/3 |
| wave（chunk 8） | 3/3 | **0/3**（1 往復だけ） |
| grip | 3/3 | 3/3 |
  → デモは毎回同じ直立姿勢から始まるので、分布の外から始めると苦手なスキルがある（限界として報告する）。次の改善案は、収集時に開始姿勢もランダムにすること。
- `a_crane/README.md`（コードの説明）、`a_crane/results/summary.csv`、`results/train_logs/*_loss.csv`、`configs/`（ベースラインで使った講義の設定）をそろえた。
- コードに氏名やメールアドレスが含まれないことを grep で確認した（a_crane 配下）。git push などの外部公開はしていない。

## 16:15 終了時点の状態
- コンテナ pai_ros2 では、GUI 版のシム（SIM=demo、ROS_DOMAIN_ID=7）と常駐の skill_server を**起動したまま**にしている（D がすぐ呼べるように）。収集用のシムは停止済み。メモリは 2.25GB / 3.5GB。
- ホストから: `docker exec -u ubuntu pai_ros2 bash /workspace/a_crane/run_skill.sh <bow|nod|wave|point_left|point_right|grip> [秒]` → 6.3 秒のスキルで全体 9.3 秒、rc=0。
- 所要時間: 13:27 開始 → 15:13 に 2 スキルを録画（18:30 の目標を達成）→ 16:15 に全項目が完了。

## 16:20〜 コーディネータからの追加 3 件
### 1. 連続実行したときの wave の信頼性
- 再現試験（`scripts/eval_sequences.sh`、常駐サーバ経由の run_skill.sh、各 5 回）:
  - 通常: point_left→wave、bow→nod、grip→wave は **すべて 5/5**（前・後のスキルとも）。
  - GPU に負荷をかけた状態（`scripts/gpu_stress.py`。4096² の行列積を回し続け、使用率 100%）でも、point_left→wave、bow→nod とも 5/5。
- 16:11 にコーディネータの試験で失敗した wave（`~/logs/runs/wave_20261101_071115.csv`）を、成功した回（071132）と比べると、軌跡はほぼ同じだった。
  - `scripts/swing_peaks.py` で、それまでの全 18 回の **2 回目の正側の振れ**を調べると +0.30〜+0.35。失敗した回は +0.30 で、閾値（>0.3）を 0.00x 下回っただけだった。
  - → **原因は「連続実行で状態が残ること」ではなく、wave の 2 回目の振りが成功の閾値すれすれだったこと**（約 1/18 の確率で落ちる）。
    サーボが遅いので、テンポ s≈1.6 だと 2 回目の振りで振幅が出ない。chunk_exec を 12 / 16 にしても 2 回目は +0.32〜0.36 で、改善しなかった。
- 対策: wave v4 = **ゆっくり・大きく**（テンポ s=2.0〜2.1、振幅 a=0.7〜0.9、シム時刻で収集。`TEMPO_RANGE` / `AMP_RANGE`）で 40 ep を収集し直し中（16:27〜）。
  閾値は変えない。nod は谷 ≈0.10（閾値 0.15）、山 ≈0.45（閾値 0.25）なので、余裕あり。
- **wave v4 の結果**: デモ自身の成功条件の通過 40/40（v3 は 34/40）。単独 5/5。振れの頂点は **+0.60 / -0.49 / +0.54 / -0.52**（v3 の 2 回目は +0.30〜0.35）で、閾値 0.3 に対して 0.2 以上の余裕ができた。
  default_seconds は 10.8 秒（ゆっくりにした分、長くなった）。skills.json の wave を v4 に差し替え、常駐サーバを再起動した。

| 連続実行（各 5 回、サーバ経由） | 修正前 (v3) | 修正後 (v4) |
|---|---|---|
| point_left → wave | 5/5, 5/5 | 5/5, 5/5 |
| bow → nod | 5/5, 5/5 | 5/5, 5/5 |
| grip → wave | 5/5, 5/5 | 5/5, 5/5 |
| （参考）GPU 負荷下 point_left→wave / bow→nod | 5/5 / 5/5 | – |
| wave の 2 回目の正側の振れ（全試行） | +0.30〜+0.35（18 回中 1 回が閾値ちょうどで失敗） | +0.53〜+0.55（直近 10 回） |
  修正前の試験では 30 回の中に失敗は出なかった（落ちる確率は約 1/18）。そのため、この修正の効果は成功回数の差ではなく、**振れの余裕（閾値に対する差）**で示す。

### 2. サーバ経由の出力に wall= を追加
- `skill_runner.run_once` が、見えている動作の壁時計の時間（方策の実行 + 直立への復帰）を記録するようにした。サーバの応答に `wall` を入れ、クライアントは
  `done: wave 10.8s home_reached=True wall=12.96s` と出力する。commander.py の正規表現 `done: .*?wall=([0-9.]+)s` に合う（d_llm は読んだだけで、変更していない）。

### 3. 自然言語のデモ動画（NL → LLM → ACT）
- `scripts/record_nl_demo.py`（WSL 側で実行）が次を順に行う。
  1. コンテナ内で ffmpeg の x11grab による録画を始める。
  2. **d_llm/commander.py を無改変で**（`--container pai_ros2 --container-env AUTO_START_SIM=0`）、指令ごとに実行し、出力の各行に時刻を付ける。
  3. 字幕を ASS/SRT で作る（上段に指令、下段に LLM の判定・応答と実行中のスキル）。動作の区間は `done: ... wall=` から決める。
  4. 字幕を焼き込み、LLM の待ち時間や docker exec の起動待ちを切り詰める。
- カメラは上から見下ろす視点（`CAM_VIEW=top`、(0.12,-0.12,1.55)、ピッチ 65°）。wave の旋回が見える。
- 指令（`scripts/nl_demo_commands.txt`。UTF-8 のファイルから読む。wsl.exe 経由の引数では日本語が空になることがあったため）:
  1. 「左を指差してから、手を振って」→ **ok**: point_left 6.4s（success=True）→ wave 10.8s（success=True、j1=[-0.51, 0.59]）
  2. 「コップを取ってきて」→ **clarify**（「…できる部分だけ実行しますか?」。確認しないので実行はされない）
  3. 「歌を歌って」→ **reject**（「歌うことはできません」）
  - 「コップを取ってきて」は、qwen2.5:3b では reject ではなく clarify になった。そのため reject の例には D の評価で reject になった「歌を歌って」を使った。
- 成果物:
  - `videos/demo_nl_commander.mp4`（**36.8 秒**、1184x928、字幕は焼き込み済み）
  - 生の録画 `videos/demo_nl_raw_164845.mp4`、字幕 `.ass` / `.srt`、区間の情報 `.json`
  - commander のログ `results/nl_demo_commander.jsonl`（パス中のユーザ名は伏せてある）
- 映像は Gazebo の 3D ビューだけを切り出している（1184x928+0+112）。デスクトップのパネル、ユーザ名、ホスト名は映らない。
- ハマりどころ: commander の stdout はパイプにつなぐとブロック単位でバッファされ、行の時刻がずれる。`python3 -u` で実行するようにした。
- ついでに: wave の単体動画を v4 + 上からの視点で撮り直した（`videos/wave_075016.mp4`。v3 版は `videos/old/` に退避）。まとめ動画 `videos/montage_a_crane.mp4`（128.9 秒）も作り直した。
- コードに埋め込んでいたユーザ固有のパスは、環境変数と ~ に置き換えた（record_nl_demo.py、plan_check.sh）。

## 16:51 追加 3 件の完了
- 常駐サーバ（wave は v4）と GUI 版のシムは起動したまま。a_crane 配下にユーザ名が含まれないことを grep で再確認した（checkpoints と動画の中身は除く）。
