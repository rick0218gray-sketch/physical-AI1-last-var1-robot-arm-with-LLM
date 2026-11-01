#!/usr/bin/env bash
# A の run_skill.sh が未完成のときの代替モック。 usage: mock_run_skill.sh <skill> [seconds]
# 実機の代わりに「実行した」ことを標準出力へ出し、指定秒だけ待つ。
skill="${1:?skill name required}"; sec="${2:-3}"
echo "[mock_run_skill] start $skill for ${sec}s"
sleep "$sec"
echo "[mock_run_skill] done  $skill"
