#!/usr/bin/env python3
"""Success criteria for one executed skill (CSV written by skill_runner.py --log).

Columns: t, s_j1, s_j2, s_j4, s_j3, s_g, a_... (joint order of /joint_states)
A run succeeds if the characteristic motion of the skill happened AND the arm came
back near HOME by the end of the policy run (|q - HOME| < 0.15 rad for arm joints,
i.e. the policy itself returned, not the forced homing afterwards).
"""
import csv
import sys

import numpy as np

HOME = np.array([0.0, 0.0, 0.0, 0.0])
TOL_HOME = 0.15


def load(path):
    rows = list(csv.DictReader(open(path)))
    g = lambda k: np.array([float(r[k]) for r in rows])
    return {k: g('s_' + k) for k in ('j1', 'j2', 'j3', 'j4', 'g')}


def crossings(x, hi, lo):
    """count alternating excursions above hi and below lo (starting with hi)"""
    n, want_hi = 0, True
    for v in x:
        if want_hi and v > hi:
            n += 1
            want_hi = False
        elif not want_hi and v < lo:
            want_hi = True
    return n


def evaluate(skill, path):
    s = load(path)
    arm_end = np.array([s['j1'][-1], s['j2'][-1], s['j3'][-1], s['j4'][-1]])
    home_err = float(np.max(np.abs(arm_end - HOME)))
    if skill == 'bow':
        motion = s['j3'].max() > 0.4
        detail = f"max_j3={s['j3'].max():.2f}"
    elif skill == 'nod':
        # valley threshold 0.15 (was 0.05): the scripted demos themselves only dip to ~0.07 because
        # the simulated wrist servo lags; checked against the demonstrations (eval_demos.py)
        n = crossings(s['j4'], 0.25, 0.15)
        motion = n >= 2
        detail = f'nods={n}'
    elif skill == 'wave':
        n = crossings(s['j1'], 0.3, -0.3)
        motion = n >= 2
        detail = f'waves={n} j1=[{s["j1"].min():.2f},{s["j1"].max():.2f}]'
    elif skill == 'point_left':
        m = (s['j1'] > 0.6) & (s['j2'] > 0.6)
        motion = m.any()
        detail = f"max_j1={s['j1'].max():.2f} max_j2={s['j2'].max():.2f}"
    elif skill == 'point_right':
        m = (s['j1'] < -0.6) & (s['j2'] > 0.6)
        motion = m.any()
        detail = f"min_j1={s['j1'].min():.2f} max_j2={s['j2'].max():.2f}"
    elif skill == 'grip':
        m = (s['g'] > -0.1) & (s['j2'] > 0.3)
        motion = m.any() and s['g'][-1] < -0.4
        detail = f"max_g={s['g'].max():.2f} end_g={s['g'][-1]:.2f}"
    else:
        raise ValueError(skill)
    ok = bool(motion and home_err < TOL_HOME)
    return ok, motion, home_err, detail


if __name__ == '__main__':
    ok, motion, err, detail = evaluate(sys.argv[1], sys.argv[2])
    print(f'success={ok} motion={motion} home_err={err:.3f} {detail}')
