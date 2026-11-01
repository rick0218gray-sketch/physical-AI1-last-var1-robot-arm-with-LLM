#!/bin/bash
# eval_lecture_infer.sh <model_path> <trials> [seconds]: run the UNMODIFIED lecture `pixi run infer`
# (wall-clock 20 Hz timer) for N seconds per trial, log /joint_states, evaluate as "bow", return home.
M=$1; N=${2:-3}; SEC=${3:-8}
export SIM=${SIM:-demo}; source /workspace/a_crane/env.sh
mkdir -p ~/logs/eval
home() { timeout 4 ros2 topic pub -r 20 /crane_plus_arm_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory \
  "{joint_names: [crane_plus_joint1, crane_plus_joint2, crane_plus_joint4, crane_plus_joint3], points: [{positions: [0,0,0,0], time_from_start: {nanosec: 100000000}}]}" > /dev/null 2>&1; }
OK=0
for k in $(seq 1 $N); do
  home
  cd "${PAI_TRAINING_ROOT:-$HOME/pai_training}"
  ~/.pixi/bin/pixi run --quiet infer --model-path $M > /dev/null 2>&1 &
  sleep 6   # pixi start + model load
  python3 /workspace/a_crane/scripts/js_logger.py ~/logs/eval/lecture_infer_$k.csv $SEC
  pkill -INT -f "[s]cripts/infer.py"; sleep 1; pkill -f "[s]cripts/infer.py"
  R=$(python3 /workspace/a_crane/scripts/eval_traj.py bow ~/logs/eval/lecture_infer_$k.csv); echo "trial $k: $R"
  echo "$R" | grep -q "success=True" && OK=$((OK+1))
done
home
echo "lecture infer.py $(basename $M) bow success $OK/$N (logged ${SEC}s after a 6 s start-up)" | tee -a ~/logs/eval/summary.txt
