# コードの来歴とローカルで確認できたライセンス

ネットワークは使用せず、素材内のファイル本文・ヘッダ・README・作業ログだけを調べた。素材には `LICENSE`、`COPYING`、`NOTICE` 原文が見つからなかった。以下のApache-2.0という表記は、確認箇所にその記述があることを示し、上流全体や依存物の適用範囲まで検証できたことは示さない。**全体に適用するLICENSEは置かない。**

| ファイル／基盤 | 分類 | 確認できた根拠 | 未確認事項 |
|---|---|---|---|
| `crane_act/launch/sim.launch.py` | 上流を改変 | 先頭2行にcrane_plus_gazebo/no_moveit_crane_plus_with_table.launch.py、Apache-2.0、RT Corporation。3行目にheadless追加 | LICENSE/NOTICE原文、改変前との差分 |
| `crane_act/scripts/train_act.py` | 上流を改変 | 2行目docstringにpai_training/scripts/train.py由来、Apache-2.0 | 上流LICENSE/NOTICE原文、ファイル群全体への適用 |
| `crane_act/scripts/convert_ext.py` | 上流を拡張 | 2行目docstringにpai_training/scripts/rosbag2lerobot.py拡張 | 当該ファイルの明示的ライセンス、元コードとの差分 |
| `crane_act/scripts/skill_runner.py` | 上流を拡張 | 冒頭docstringにpai_training/scripts/infer.py拡張 | 同上 |
| `crane_act/configs/*.yaml` | 講義設定を変更 | 作業ログ13:37–13:50、16:05–16:15。バッチ・学習ステップ等を調整。データパスは相対化 | 元設定の著作権・ライセンス |
| `crane_act/scripts/debug_policy_save.py` | 自作ラッパ、講義コードを外部参照 | docstringとrunpy呼出し。講義debug_policy.pyは無改変実行、本体は同梱なし | 外部スクリプトのライセンス |
| `crane_act/scripts/skills.py`、`auto_demo.py` | 自動デモ生成の自作部分（AI支援含む） | 作業ログ13:30以降とcrane_act README。physicalai_teleopと同じ関節順序・定数を使う旨のコメントあり | 全行単位の由来、physicalai_teleopのLICENSE原文 |
| `crane_act/scripts/make_submission_video.py` | 自作（AI支援含む） | 提出動画の組み立て。録画済みの動画とffmpegのみを使用 | なし |
| `crane_act` のその他の `.py` / `.sh`、env、スキルJSON | 課題用の実行・評価・運用補助として記録 | crane_act READMEのFiles、作業ログ各実装項目に対応。常駐サーバ・収集・評価・録画等 | 一つずつの上流との差分が素材にない。完全な新規著作物という断定は要確認 |
| `nl_commander/commander.py`、`overlay.py`、`eval/*.py`、mock・hints・テスト・字幕 | 課題用の言語計画・評価・可視化として記録 | 言語計画の作業ログ13:40–14:20「実装」、nl_commander README | 上流コードの混入の有無の全行照合、個別ライセンス指定 |
| 学習済み重み、図表、動画 | 当該実験の出力として記録 | 作業ログとモデル付属メタ情報、評価ログ | モデル・ロボットアセット等の再配布条件 |
| matsuolab/pai_training | 依存・派生元 | crane_act README末尾でApache-2.0、train_actヘッダでもApache-2.0 | 上流LICENSE/NOTICE原文、バージョン、全ファイル適用範囲 |
| physicalai_teleop、LeRobot | 依存・参考 | 作業ログのclone/build、コードのコメント・import | ライセンス原文・バージョンとも未確認 |

時間系・観測・学習と実行の改良、言語による計画と逐次実行を独自の工夫として説明する。「自作」は作業ログに記された課題用実装という区分で、上流を一切使わないという意味ではない。

## 公開用に施した変更

- 作業時の `a_crane / d_llm` を `crane_act / nl_commander` に配置。
- 個人プロファイルに依存するパスを相対パス・ホーム表記に置換。JSONLの実行コマンドは `docker.exe` に短縮。過去のログ中の旧ディレクトリ名は実験記録として保持。
- commanderの兄弟参照を `crane_act` にし、個人専用のDocker実行パス候補を除去。PATHまたは `COMMANDER_DOCKER` を利用。
- `PAI_TRAINING_ROOT` を変数化し、debug-policyラッパのホーム展開を明示。YAMLのパスは講義環境からの相対配置へ変更。
- テキストは原則UTF-8・LFへ統一。`.gitattributes` はgitでのテキスト改行をLFに統一する。
- 学習や物理パラメータの再調整は行っていない。

作業ログの実験はClaude支援の記録を含む。ファイル整理・検査・草稿作成にはCodexとClaudeを使用した。
