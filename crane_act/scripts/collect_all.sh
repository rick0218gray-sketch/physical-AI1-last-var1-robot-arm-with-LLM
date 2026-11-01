#!/bin/bash
# sequentially collect all extension skills (headless sim must be running)
N=${1:-40}
for sk in point_left wave nod point_right grip; do
  echo "== $sk $(date)"
  bash /workspace/a_crane/scripts/collect.sh $sk $N 1 > ~/logs/collect_$sk.log 2>&1
done
echo "== all done $(date)"
