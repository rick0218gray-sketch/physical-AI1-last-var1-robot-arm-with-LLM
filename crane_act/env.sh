# source this inside the container (user ubuntu)
source /opt/ros/humble/setup.bash
source ~/airobot_ws/install/setup.bash
[ -f ~/pai_ws/install/setup.bash ] && source ~/pai_ws/install/setup.bash
export DISPLAY=${DISPLAY:-:0}
export A_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PAI_TRAINING_ROOT="${PAI_TRAINING_ROOT:-$HOME/pai_training}"
# Two independent simulations can run side by side:
#   SIM=collect (default): ROS_DOMAIN_ID=0, headless data collection
#   SIM=demo            : ROS_DOMAIN_ID=7, GUI on the VNC desktop for inference / recording
if [ "${SIM:-collect}" = "demo" ]; then
  export ROS_DOMAIN_ID=7; export IGN_PARTITION=demo
else
  export ROS_DOMAIN_ID=0; export IGN_PARTITION=collect
fi
