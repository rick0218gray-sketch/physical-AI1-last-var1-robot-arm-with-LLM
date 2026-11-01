#!/bin/bash
# skill_server.sh start|stop|status  -- resident policy server (see skill_server.py), SIM=demo by default
export SIM=${SIM:-demo}
source /workspace/a_crane/env.sh
case "$1" in
  start)
    if python3 /workspace/a_crane/scripts/skill_client.py __ping__ >/dev/null 2>&1; then echo "already running"; exit 0; fi
    cd "${PAI_TRAINING_ROOT:-$HOME/pai_training}"
    nohup ~/.pixi/bin/pixi run --quiet python /workspace/a_crane/scripts/skill_server.py > ~/logs/skill_server.log 2>&1 &
    for i in $(seq 1 90); do sleep 1; grep -q "server ready" ~/logs/skill_server.log && { grep "server ready" ~/logs/skill_server.log; exit 0; }; done
    echo "server did not start"; tail -5 ~/logs/skill_server.log; exit 1;;
  stop)
    for p in $(pgrep -f "[s]kill_server.py"); do kill $p; done; sleep 2
    for p in $(pgrep -f "[s]kill_server.py"); do kill -9 $p; done; echo stopped;;
  status)
    python3 /workspace/a_crane/scripts/skill_client.py __ping__;;
esac
