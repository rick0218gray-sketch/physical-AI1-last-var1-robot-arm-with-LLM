#!/bin/bash
# demo_record.sh <skill> [seconds] [label]  -> /workspace/a_crane/videos/<skill>_<time>.mp4
# Runs run_skill.sh and records the Gazebo view from the moment the policy is ready
# (skill_runner touches $START_MARKER) until 1.5 s after the arm is back upright.
SK=$1; SEC=${2:-}; LABEL=${3:-"ACT policy - $SK"}
A=/workspace/a_crane
OUT=$A/videos/${SK}_$(date +%H%M%S).mp4
export START_MARKER=/tmp/skill_started_$$ START_DELAY=1.0
rm -f $START_MARKER
bash $A/run_skill.sh $SK $SEC > /tmp/demo_record_$$.log 2>&1 &
RUN=$!
for i in $(seq 1 600); do [ -f $START_MARKER ] && break; sleep 0.1; done
bash $A/scripts/record.sh $OUT 120 "$LABEL" &
wait $RUN
sleep 1.5
pkill -INT -f "[f]fmpeg.*x11grab"; wait
cat /tmp/demo_record_$$.log | grep -E "success|done"
rm -f $START_MARKER /tmp/demo_record_$$.log
echo "video: $OUT"
