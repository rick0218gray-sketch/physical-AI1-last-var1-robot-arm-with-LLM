#!/bin/bash
# cpu_jobs.sh pause|resume : SIGSTOP/SIGCONT CPU training jobs (to give the simulation the CPU)
SIG=$([ "$1" = "pause" ] && echo STOP || echo CONT)
for p in $(pgrep -f "[t]rain_act.py.*--device cpu"); do kill -$SIG $p; done
echo "$1: $(pgrep -f '[t]rain_act.py.*--device cpu' | tr '\n' ' ')"
