#!/bin/bash
# record.sh <out.mp4> <seconds> [label]
# grabs the Gazebo 3D view on the VNC display :0 (window placed by gazebo_window.sh) with ffmpeg x11grab
OUT=$1; SEC=${2:-15}; LABEL=${3:-}
mkdir -p $(dirname $OUT)
FONT=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
VF="null"
if [ -n "$LABEL" ] && [ -f $FONT ]; then
  VF="drawtext=fontfile=$FONT:text='${LABEL//:/ -}':x=20:y=20:fontsize=30:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=8"
fi
ffmpeg -loglevel error -y -f x11grab -draw_mouse 0 -video_size 1184x928 -framerate 20 -i :0.0+0,112 -t $SEC \
  -vf "$VF" -c:v libx264 -preset veryfast -crf 24 -pix_fmt yuv420p $OUT
