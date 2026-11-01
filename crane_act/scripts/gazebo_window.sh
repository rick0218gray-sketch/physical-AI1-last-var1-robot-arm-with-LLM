#!/bin/bash
# prepare the Gazebo GUI (SIM=demo) for recording: place/resize the window and point the camera at the arm
export DISPLAY=:0
export SIM=${SIM:-demo}
source /workspace/a_crane/env.sh
# the MATE screensaver ("floaters" logos) kicks in after a few idle minutes and paints over the recording
P=$(pgrep -x mate-session | head -1)
[ -n "$P" ] && export $(tr '\0' '\n' < /proc/$P/environ | grep DBUS_SESSION_BUS_ADDRESS)
gsettings set org.mate.screensaver idle-activation-enabled false 2>/dev/null
gsettings set org.mate.screensaver lock-enabled false 2>/dev/null
mate-screensaver-command --deactivate > /dev/null 2>&1
xdotool mousemove 1915 1075
for W in $(wmctrl -l | awk '$4=="Gazebo" && $5=="GUI"{print $1}'); do xdotool windowminimize $W 2>/dev/null; done
for W in $(wmctrl -l | awk '$4=="Gazebo" && NF==4{print $1}'); do
  wmctrl -i -r $W -b remove,maximized_vert,maximized_horz
  xdotool windowmove $W 0 28 windowsize $W 1600 1000; wmctrl -i -a $W
done
sleep 1
if [ "${CAM_VIEW:-}" = "top" ]; then
  CAM_X=${CAM_X:-0.12}; CAM_Y=${CAM_Y:--0.12}; CAM_Z=${CAM_Z:-1.55}; CAM_Q="w: 0.3228, x: -0.4964, y: 0.2056, z: 0.7792"
fi
# camera at (0.42,-0.42,1.36) looking at the arm (yaw 135 deg, pitch 21 deg)
ign service -s /gui/move_to/pose --reqtype ignition.msgs.GUICamera --reptype ignition.msgs.Boolean --timeout 3000 \
  --req "pose: {position: {x: ${CAM_X:-0.42}, y: ${CAM_Y:--0.42}, z: ${CAM_Z:-1.36}}, orientation: {${CAM_Q:-w: 0.3762, x: -0.1691, y: 0.0700, z: 0.9083}}}"
# top-down variant (pitch 65 deg) for skills that rotate about the base (wave):
#   CAM_VIEW=top -> camera (0.12,-0.12,1.55)
echo "gazebo window ready"
