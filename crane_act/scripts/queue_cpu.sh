#!/bin/bash
# ablations (CPU, sequential): data size and observation type on bow
B=/workspace/a_crane/scripts/build_and_train.sh
export DEVICE=cpu
bash $B bow 10 phase 2500
bash $B bow 50 state 2500
bash $B bow 30 phase 2500
echo "queue_cpu finished $(date)"
