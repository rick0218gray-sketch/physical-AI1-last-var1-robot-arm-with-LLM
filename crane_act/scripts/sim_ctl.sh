#!/bin/bash
# sim_ctl.sh start [gui=true|false] | stop | status
#   SIM=collect (default, ROS_DOMAIN_ID=0) or SIM=demo (ROS_DOMAIN_ID=7), see env.sh
source /workspace/a_crane/env.sh
LOG=~/sim_${SIM:-collect}.log

# list PIDs matching a pattern that belong to this SIM (decided by ROS_DOMAIN_ID in /proc/<pid>/environ)
mine() {
  for p in $(pgrep -f "$1"); do
    if tr '\0' '\n' < /proc/$p/environ 2>/dev/null | grep -qx "ROS_DOMAIN_ID=7"; then d=7; else d=0; fi
    [ "$d" = "$ROS_DOMAIN_ID" ] && echo $p
  done
}

case "$1" in
  start)
    GUI=${2:-true}
    nohup ros2 launch /workspace/a_crane/launch/sim.launch.py gui:=$GUI > $LOG 2>&1 &
    for i in $(seq 1 60); do
      sleep 1
      if [ $(grep -c "Configured and activated" $LOG) -ge 3 ]; then echo "sim ready (gui=$GUI) after ${i}s"; exit 0; fi
    done
    echo "sim not ready"; exit 1;;
  stop)
    for p in $(mine "sim.launch.py"); do kill -INT $p; done; sleep 3
    for pat in "ign gazebo" parameter_bridge robot_state_publisher; do
      for p in $(mine "$pat"); do kill $p 2>/dev/null; done
    done
    sleep 1; echo "stopped (domain $ROS_DOMAIN_ID)";;
  status)
    mine "ign gazebo" | xargs -r ps -o pid,args -p || echo "not running";;
esac
