#!/bin/bash
# all models on the GPU, sequential (sim-clock datasets)
B=/workspace/a_crane/scripts/build_and_train.sh
for sk in point_left wave nod point_right grip; do bash $B $sk 40 phase 2500; done
bash $B bow 50 state 2500
bash $B bow 10 phase 2500
bash $B bow 30 phase 2500
echo "queue_gpu finished $(date)"
