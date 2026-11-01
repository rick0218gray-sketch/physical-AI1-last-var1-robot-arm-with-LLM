#!/bin/bash
# collect.sh <skill> <episodes> [seed] [start_index]  -> ~/dataset/rosbags/<skill>${TAG}/ep_XXX
source /workspace/a_crane/env.sh
python3 /workspace/a_crane/scripts/auto_demo.py --skill $1 --episodes $2 --seed ${3:-0} \
  --start-index ${4:-0} --out ~/dataset/rosbags/$1${TAG:-} 2>&1 | grep --line-buffered -v "terminate called"
