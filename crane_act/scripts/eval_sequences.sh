#!/bin/bash
# eval_sequences.sh <reps> <tag> "a>b" "c>d" ...  -- run skill pairs back-to-back through run_skill.sh
# (resident server path) and count the success of each step. Appends to ~/logs/eval/sequences.txt
R=$1; TAG=$2; shift 2
for pair in "$@"; do
  A=${pair%%>*}; B=${pair##*>}; okA=0; okB=0
  for k in $(seq 1 $R); do
    oa=$(bash /workspace/a_crane/run_skill.sh $A | grep success=); ob=$(bash /workspace/a_crane/run_skill.sh $B | grep success=)
    echo "$TAG $A>$B rep$k | $A: $oa | $B: $ob" >> ~/logs/eval/sequences_detail.txt
    echo "$oa" | grep -q success=True && okA=$((okA+1)); echo "$ob" | grep -q success=True && okB=$((okB+1))
  done
  echo "$TAG $A>$B : $A $okA/$R, $B $okB/$R" | tee -a ~/logs/eval/sequences.txt
done
