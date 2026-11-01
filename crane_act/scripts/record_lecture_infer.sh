#!/bin/bash
# record the UNMODIFIED lecture infer.py with the baseline bow model (for the before/after comparison)
export SIM=${SIM:-demo}; source /workspace/a_crane/env.sh
A=/workspace/a_crane
M=${1:-$HOME/checkpoints/train/crane_plus_pekori_act}
OUT=$A/videos/baseline_lecture_infer_$(date +%H%M%S).mp4
python3 $A/scripts/skill_client.py __ping__ > /dev/null && bash $A/run_skill.sh bow 0.1 > /dev/null  # make sure we start upright
cd "${PAI_TRAINING_ROOT:-$HOME/pai_training}"
~/.pixi/bin/pixi run --quiet infer --model-path $M > /dev/null 2>&1 &
sleep 5
bash $A/scripts/record.sh $OUT 14 "BASELINE - lecture infer.py, wall-clock 20 Hz (bow, 20 demos)"
pkill -INT -f "[s]cripts/infer.py"; sleep 1; pkill -f "[s]cripts/infer.py"
timeout 4 ros2 topic pub -r 20 /crane_plus_arm_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory \
  "{joint_names: [crane_plus_joint1, crane_plus_joint2, crane_plus_joint4, crane_plus_joint3], points: [{positions: [0,0,0,0], time_from_start: {nanosec: 100000000}}]}" > /dev/null 2>&1
echo "video: $OUT"
