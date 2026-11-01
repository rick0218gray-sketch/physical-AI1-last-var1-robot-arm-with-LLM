#!/usr/bin/env python3
"""rosbag2 -> LeRobotDataset v2.1 (extended version of pai_training/scripts/rosbag2lerobot.py)

Differences from the lecture converter:
  * non-interactive (--overwrite), episode subset (--max-episodes) for data-size studies
  * --env-mode phase : observation.environment_state = [t_since_start, dq1..dq4]
        t_since_start : seconds since the episode started (phase of the skill)
        dqk           : joint k displacement over the last 0.1 s (velocity proxy)
    This resolves the ambiguity of "same joint angles on the way down / way up"
    and "upright at the start / upright at the end" that a state-only policy has.
  * --env-mode phase (final): environment_state = [t, 0, 0, 0, 0]  (time only)
    --env-mode phasedq (first try, see log): [t, dq1..dq4] -> copycat problem in closed loop
  * episodes are trimmed so that the motion always starts 0.25 s after frame 0 (--lead)
  * time base = simulation clock (--clock sim): the sim runs at RTF 0.55-0.9 depending on load,
    so wall-clock data/control do not transfer between collection and inference.
  * --env-mode state : identical to the lecture (environment_state = state)

Run inside pai_training's pixi env:
  cd ~/pai_training && pixi run python /workspace/a_crane/scripts/convert_ext.py \
      --bags ~/dataset/rosbags/bow --out ~/dataset/lerobot_dataset/bow_phase --repo-id bow_phase --env-mode phase
"""
import argparse
import shutil
from pathlib import Path

import numpy as np
import torch
from rosbags.rosbag2 import Reader
from rosbags.serde import deserialize_cdr
from lerobot.common.datasets.lerobot_dataset import LeRobotDataset

JS_ORDER = ['crane_plus_joint1', 'crane_plus_joint2', 'crane_plus_joint4', 'crane_plus_joint3', 'crane_plus_joint_hand']
ARM_ORDER = ['crane_plus_joint1', 'crane_plus_joint2', 'crane_plus_joint4', 'crane_plus_joint3']
FPS = 20
DQ_LAG = 2  # frames (0.1 s)


def features():
    names = ["joint1", "joint2", "joint4", "joint3", "gripper"]
    return {
        "observation.state": {"dtype": "float32", "shape": (5,), "names": names},
        "observation.environment_state": {"dtype": "float32", "shape": (5,), "names": names},
        "action": {"dtype": "float32", "shape": (5,), "names": names},
    }


def env_state(mode, states, i):
    if mode == 'state':
        return states[i]
    if mode == 'phase':
        return np.array([i / FPS, 0, 0, 0, 0], dtype=np.float32)
    prev = states[max(0, i - DQ_LAG)]
    # order of states: j1, j2, j4, j3, hand  -> dq for the four arm joints (same order)
    return np.concatenate([[i / FPS], states[i][:4] - prev[:4]]).astype(np.float32)


def read_episode(ep_dir, clock='sim'):
    msgs = {'/joint_states': [], '/crane_plus_arm_controller/joint_trajectory': [],
            '/crane_plus_gripper_controller/joint_trajectory': []}
    with Reader(ep_dir) as r:
        conns = [c for c in r.connections if c.topic in msgs]
        for c, ts, raw in r.messages(connections=conns):
            msgs[c.topic].append((deserialize_cdr(raw, c.msgtype), ts))
    js, arm, grip = (msgs[k] for k in msgs)
    jt = np.array([t for _, t in js])
    if clock == 'sim':
        # Re-time everything on the SIMULATION clock: /joint_states carries the sim time in its
        # header, the commands (no stamp) are mapped wall->sim by interpolating that relation.
        js_sim = np.array([m.header.stamp.sec * 1e9 + m.header.stamp.nanosec for m, _ in js])
        to_sim = lambda w: np.interp(np.asarray(w, dtype=float), jt.astype(float), js_sim)
        arm = [(m, to_sim(t)) for m, t in arm]
        grip = [(m, to_sim(t)) for m, t in grip]
        jt = js_sim
    jp = np.array([[dict(zip(m.name, m.position))[n] for n in JS_ORDER] for m, _ in js])
    at = np.array([t for _, t in arm])
    ap = np.array([[dict(zip(m.joint_names, m.points[0].positions))[n] for n in ARM_ORDER] for m, _ in arm])
    gt = np.array([t for _, t in grip])
    gp = np.array([m.points[0].positions[0] for m, _ in grip])
    start = max(jt[0], at[0], gt[0])
    end = min(jt[-1], at[-1], gt[-1])
    n = int((end - start) * FPS / 1e9)
    tt = start + np.arange(n) * (1e9 / FPS)

    def hold(times, vals):
        idx = np.clip(np.searchsorted(times, tt, side='right') - 1, 0, None)
        return np.asarray(vals)[idx]
    states = hold(jt, jp).astype(np.float32)
    actions = np.hstack([hold(at, ap), hold(gt, gp).reshape(-1, 1)]).astype(np.float32)
    return states, actions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bags', required=True, nargs='+')
    ap.add_argument('--out', required=True)
    ap.add_argument('--repo-id', required=True)
    ap.add_argument('--task', default=None)
    ap.add_argument('--env-mode', choices=['state', 'phase', 'phasedq'], default='phase')
    ap.add_argument('--max-episodes', type=int, default=0)
    ap.add_argument('--clock', choices=['sim', 'wall'], default='sim',
                    help='time base for resampling at 20 Hz (sim: robust to the real-time factor)')
    ap.add_argument('--lead', type=float, default=0.25,
                    help='trim each episode so that the first commanded motion starts LEAD s after frame 0 (<0: no trim)')
    ap.add_argument('--pad-to', type=int, default=0, help='pad every episode to this many frames (0 = longest)')
    args = ap.parse_args()

    ep_dirs = []
    for b in args.bags:
        ep_dirs += sorted(p.parent for p in Path(b).expanduser().rglob('*.db3'))
    if args.max_episodes:
        ep_dirs = ep_dirs[:args.max_episodes]
    out = Path(args.out).expanduser()
    if out.exists():
        shutil.rmtree(out)
    ds = LeRobotDataset.create(repo_id=args.repo_id, fps=FPS, root=out, robot_type='crane_plus',
                               features=features(), use_videos=True)
    eps = [read_episode(d, args.clock) for d in ep_dirs]
    if args.lead >= 0:
        trimmed = []
        for st, ac in eps:
            moving = np.where(np.max(np.abs(ac - ac[0]), axis=1) > 1e-3)[0]
            k0 = max(0, (moving[0] if len(moving) else 0) - int(round(args.lead * FPS)))
            trimmed.append((st[k0:], ac[k0:]))
        eps = trimmed
    pad = args.pad_to or max(len(s) for s, _ in eps)
    task = args.task or args.repo_id
    for k, (states, actions) in enumerate(eps):
        n = len(states)
        for i in range(pad):
            j = min(i, n - 1)
            # padded frames: time keeps advancing, robot stays (dq = 0)
            es = env_state(args.env_mode, states, j)
            if args.env_mode != 'state' and i >= n:
                es = np.concatenate([[i / FPS], np.zeros(4)]).astype(np.float32)
            ds.add_frame({"observation.state": torch.tensor(states[j]),
                          "observation.environment_state": torch.tensor(es),
                          "action": torch.tensor(actions[j]), "task": task})
        ds.save_episode()
        print(f'episode {k}: {n} frames (padded to {pad}) from {ep_dirs[k]}', flush=True)
    print('saved', out, 'episodes', len(eps))


if __name__ == '__main__':
    main()
