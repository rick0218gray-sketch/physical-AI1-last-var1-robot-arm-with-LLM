#!/bin/bash
# measure real-time factor of the running simulation (sim seconds / wall seconds)
source /workspace/a_crane/env.sh
a=$(timeout 5 ros2 topic echo --once /clock | grep sec: | head -1 | awk '{print $2}'); ta=$(date +%s)
sleep ${1:-10}
b=$(timeout 5 ros2 topic echo --once /clock | grep sec: | head -1 | awk '{print $2}'); tb=$(date +%s)
python3 -c "print('RTF ~', round(($b-$a)/($tb-$ta),2))"
