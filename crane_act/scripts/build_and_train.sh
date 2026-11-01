#!/bin/bash
# build_and_train.sh <skill> <n_episodes> <phase|state> <steps>
# -> dataset ~/dataset/lerobot_dataset/<skill>_n<N>_<mode>, checkpoint ~/checkpoints/<skill>_n<N>_<mode>
SK=$1; N=$2; MODE=$3; STEPS=${4:-3000}
NAME=${SK}_n${N}_${MODE}${SUFFIX:-}
source /workspace/a_crane/env.sh >/dev/null 2>&1
cd "${PAI_TRAINING_ROOT:-$HOME/pai_training}"
PIXI=~/.pixi/bin/pixi
mkdir -p ~/logs
echo "[$(date +%H:%M:%S)] convert $NAME"
$PIXI run --quiet python /workspace/a_crane/scripts/convert_ext.py --bags ~/dataset/rosbags/${BAGS:-$SK} \
   --out ~/dataset/lerobot_dataset/$NAME --repo-id $NAME --task $SK --env-mode $MODE --max-episodes $N \
   > ~/logs/convert_$NAME.log 2>&1 || { echo convert failed; tail ~/logs/convert_$NAME.log; exit 1; }
echo "[$(date +%H:%M:%S)] train $NAME ($STEPS steps)"
$PIXI run --quiet python /workspace/a_crane/scripts/train_act.py --dataset-root ~/dataset/lerobot_dataset/$NAME \
   --repo-id $NAME --out ~/checkpoints/$NAME --steps $STEPS --device ${DEVICE:-cuda} ${TRAIN_EXTRA:-} > ~/logs/train_$NAME.log 2>&1 || { echo train failed; tail ~/logs/train_$NAME.log; exit 1; }
echo "[$(date +%H:%M:%S)] done $NAME: $(tail -1 ~/logs/train_$NAME.log)"
