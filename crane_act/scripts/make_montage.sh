#!/bin/bash
# concatenate the demo clips into one ~2 min video: videos/montage_a_crane.mp4
V=/workspace/a_crane/videos
FONT=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
card() {  # card <out> <seconds> <line1> <line2>
  ffmpeg -loglevel error -y -f lavfi -i color=c=0x202830:s=1184x928:r=20 -t $2 \
    -vf "drawtext=fontfile=$FONT:text='$3':fontcolor=white:fontsize=44:x=(w-tw)/2:y=h/2-60,drawtext=fontfile=$FONT:text='$4':fontcolor=0xbbbbbb:fontsize=28:x=(w-tw)/2:y=h/2+10" \
    -c:v libx264 -preset veryfast -crf 24 -pix_fmt yuv420p $1
}
T=/tmp/montage; rm -rf $T; mkdir -p $T
card $T/00.mp4 3 "CRANE+ V2 - ACT from scripted demos" "6 skills, 250 auto-generated demos, Gazebo"
card $T/01.mp4 2 "Baseline (lecture pipeline)" "bow, 20 demos - lecture infer.py vs improved runner"
card $T/03.mp4 2 "Improved pipeline" "time-conditioned ACT, sim-clock control, lag augmentation"
L=$T/list.txt; : > $L
add() { [ -f "$1" ] && echo "file '$1'" >> $L; }
add $T/00.mp4; add $T/01.mp4
add $(ls $V/baseline_lecture_infer_*.mp4 | tail -1); add $(ls $V/baseline_model_improved_runner_*.mp4 | tail -1)
add $T/03.mp4
for s in bow point_left point_right grip wave nod; do add $(ls $V/${s}_*.mp4 | tail -1); done
ffmpeg -loglevel error -y -f concat -safe 0 -i $L -c:v libx264 -preset veryfast -crf 24 -pix_fmt yuv420p -r 20 $V/montage_a_crane.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 $V/montage_a_crane.mp4
