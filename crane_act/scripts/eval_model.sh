#!/bin/bash
# eval_model.sh <skill> <checkpoint_name|path> <trials> [seconds]  (on SIM=demo by default)
SK=$1; M=$2; N=${3:-5}; SEC=${4:-}
[ -d "$M" ] || M=~/checkpoints/$M
if [ -z "$SEC" ]; then SEC=$(python3 -c "import json;print(json.load(open('/workspace/a_crane/skills.json')).get('$SK',{}).get('default_seconds',8))" 2>/dev/null || echo 8); fi
export SIM=${SIM:-demo}
source /workspace/a_crane/env.sh
mkdir -p ~/logs/eval
TAG=$(basename $M)_$(date +%H%M%S)
cd "${PAI_TRAINING_ROOT:-$HOME/pai_training}"
~/.pixi/bin/pixi run --quiet python /workspace/a_crane/scripts/skill_runner.py --model-path $M --seconds $SEC ${RUNNER_EXTRA:-} \
   --trials $N --eval-skill $SK --log ~/logs/eval/$TAG.csv 2>&1 | grep -E "^trial|^done" | tee ~/logs/eval/$TAG.txt
echo "$(basename $M) $SK success $(grep -c 'success=True' ~/logs/eval/$TAG.txt)/$N" | tee -a ~/logs/eval/summary.txt
