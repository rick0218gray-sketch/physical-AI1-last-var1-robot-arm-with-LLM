# a_crane: ACT skills for CRANE+ V2 from scripted demonstrations

Extension of the Physical AI course pipeline (Gazebo CRANE+ V2 -> rosbag -> LeRobotDataset -> ACT -> Gazebo):
the keyboard teleoperation is replaced by an **automatic demonstration generator**, and six skills
(bow, nod, wave, point_left, point_right, grip) are learned as separate ACT policies.

Runs inside the `airobotbook/ros2-desktop-ai-robot-book-humble` container (user `ubuntu`), with
`pai_training` (pixi env) in `~/pai_training` and this directory mounted at `/workspace/a_crane`.

## Key changes vs. the lecture pipeline
| problem found | fix (file) |
|---|---|
| state-only observation cannot tell "going down" from "coming back" / start from end | `observation.environment_state = [t, 0,0,0,0]` (time since skill start), episodes aligned 0.25 s before motion (`scripts/convert_ext.py --env-mode phase`) |
| real-time factor of Gazebo changes with load (0.55-0.92), wall-clock data/control do not transfer | resample on the **simulation clock** (`/joint_states` header stamps) and run the policy at 20 Hz of sim time (`scripts/skill_runner.py`); demos stepped on sim time (`SIM_TIME=1`) |
| servos lag more at inference than during collection | **lag augmentation**: observe the state 0-8 frames earlier during training (`scripts/train_act.py --lag-aug`) |
| joints a skill never moves have std ~ 0 -> exploding normalised inputs | clamp std >= 0.05 rad (`--min-std`) |
| periodic skills (wave/nod) drift in phase in closed loop | fixed tempo + execute 8 chunk steps open-loop (`--chunk-exec 8`, stored in `a_crane_meta.json`) |
| wave's 2nd swing only reached ~0.3 rad (servo lag) | wave v4 demos: slower tempo (x2.0-2.1) and larger amplitude (0.7-0.9) |
| lecture DataLoader re-spawns workers every epoch (slow) | dataset cached as tensors on the GPU, chunks built from parquet columns (`train_act.py`) |

## Files
- `run_skill.sh <skill> [seconds]` - run one skill, then return upright (uses the resident server if running)
- `skills.json` - skill name -> `{model_path, description, default_seconds}`
- `checkpoints/<skill>/` - final ACT policies (small ACT: dim 256, 2 encoder layers)
- `launch/sim.launch.py` - CRANE+ V2 + table without MoveIt, `gui:=false` for headless collection
- `scripts/skills.py` - scripted skill library (min-jerk keyframes, randomised amplitude/target/tempo)
- `scripts/auto_demo.py`, `scripts/collect.sh` - automatic demo generation + per-episode `ros2 bag record`
- `scripts/convert_ext.py` - rosbag2 -> LeRobotDataset (sim clock, phase observation, subsets)
- `scripts/train_act.py`, `scripts/build_and_train.sh` - training
- `scripts/skill_runner.py`, `scripts/skill_server.py`, `scripts/skill_client.py`, `scripts/skill_server.sh` - inference (one-shot or resident)
- `scripts/eval_traj.py`, `scripts/eval_model.sh`, `scripts/eval_demos.py`, `scripts/eval_lecture_infer.sh` - evaluation
- `scripts/debug_policy_save.py` - lecture `debug_policy.py`, plot saved to PNG
- `scripts/sim_ctl.sh`, `scripts/gazebo_window.sh`, `scripts/record.sh`, `scripts/demo_record.sh`, `scripts/make_montage.sh` - simulation / recording
- `scripts/eval_sequences.sh`, `scripts/swing_peaks.py`, `scripts/gpu_stress.py` - back-to-back skill tests / swing amplitude margin
- `scripts/record_nl_demo.py`, `scripts/nl_demo_commands.txt`, `scripts/plan_check.sh` - NL -> LLM (d_llm/commander.py, used read-only) -> ACT demo recording with burned-in subtitles (run on the WSL host)
- `results/` - evaluation summary, debug-policy plots, training loss curves; `videos/` - recordings

## Quick start (inside the container)
```bash
SIM=demo bash /workspace/a_crane/scripts/sim_ctl.sh start true      # Gazebo with GUI (ROS_DOMAIN_ID=7)
bash /workspace/a_crane/scripts/skill_server.sh start                # keep all policies loaded
bash /workspace/a_crane/run_skill.sh wave                            # -> success=True ...
# data collection / training (headless sim on domain 0)
bash /workspace/a_crane/scripts/sim_ctl.sh start false
SIM_TIME=1 bash /workspace/a_crane/scripts/collect.sh bow 50 0
bash /workspace/a_crane/scripts/build_and_train.sh bow 50 phase 2500
```
Third-party code: `launch/sim.launch.py` is based on crane_plus_gazebo (Apache-2.0, RT Corporation);
`train_act.py`, `skill_runner.py`, `convert_ext.py` are based on matsuolab/pai_training (Apache-2.0) and LeRobot.

## ステージング時の注記
上のApache-2.0表記は元READMEの記述を保持したものです。ヘッダの確認と上流LICENSE原文の確認は区別し、今回の確認範囲を [来歴](../docs/provenance.md) に記載しました。
