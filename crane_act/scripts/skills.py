"""Scripted skill library for CRANE+ V2 (auto demo generation).

Every skill is a list of keyframes (duration_sec, [j1, j2, j3, j4, gripper]) in
*semantic* joint order. The motion between keyframes uses minimum-jerk
interpolation, so the arm never stops abruptly in the middle of a skill.
All skills start and end at HOME (upright, gripper open), which keeps the
initial pose identical across episodes.
Randomisation (amplitude / speed / target) is drawn from a numpy Generator,
but the *structure* (direction of the first swing, number of cycles) is fixed
so that the demonstrations stay uni-modal.
"""
import numpy as np

GRIPPER_OPEN = -0.5236   # same values as physicalai_teleop
GRIPPER_CLOSE = 0.1745
HOME = np.array([0.0, 0.0, 0.0, 0.0, GRIPPER_OPEN])
import os as _os
FIXED_TEMPO = _os.environ.get('FIXED_TEMPO', '0') == '1'

DESCRIPTIONS = {
    'bow': 'お辞儀: 肘(joint3)を前に倒して戻す',
    'nod': 'うなずき: 手首(joint4)を2回上下させる',
    'wave': '手を振る: 前腕を少し倒し、旋回(joint1)を左右に2往復',
    'point_left': '左を指差す: 旋回(joint1)を左へ、腕を水平に伸ばして戻る',
    'point_right': '右を指差す: 旋回(joint1)を右へ、腕を水平に伸ばして戻る',
    'grip': 'つかむ: 前方へ手を伸ばしてグリッパを閉じ、持ち上げて戻り開く',
}


def _pose(j1=0.0, j2=0.0, j3=0.0, j4=0.0, g=GRIPPER_OPEN):
    return np.array([j1, j2, j3, j4, g], dtype=float)


def make_keyframes(skill, rng):
    u = rng.uniform
    s = u(1.3, 1.9)             # global speed factor (duration multiplier); the simulated servos are slow
    if skill in ('wave', 'nod') and FIXED_TEMPO:
        # v2: periodic skills keep a (nearly) fixed tempo. With a random tempo the k-th swing happens at
        # very different times across demos, and a time-conditioned policy averages them into a flat line.
        lo, hi = (float(v) for v in _os.environ.get('TEMPO_RANGE', '1.55,1.65').split(','))
        s = u(lo, hi)
    kf = []
    if skill == 'bow':
        a = u(0.6, 1.1)
        kf = [(1.0 * s, _pose(j3=a)), (u(0.2, 0.4), _pose(j3=a)), (1.0 * s, HOME)]
    elif skill == 'nod':
        a = u(0.4, 0.8)
        for _ in range(2):
            kf += [(0.6 * s, _pose(j4=a)), (0.6 * s, _pose(j4=-0.15 * a))]
        kf += [(0.4 * s, HOME)]
    elif skill == 'wave':
        # v4: AMP_RANGE=0.7,0.9 (bigger swings; the 2nd swing of v3 only reached ~0.3 rad because the servo lags)
        alo, ahi = (float(v) for v in _os.environ.get('AMP_RANGE', '0.5,0.9').split(','))
        a = u(alo, ahi)
        lean = u(0.3, 0.5)
        kf = [(0.6 * s, _pose(j3=lean, j4=lean))]
        for _ in range(2):
            kf += [(0.6 * s, _pose(j1=a, j3=lean, j4=lean)),
                   (0.6 * s, _pose(j1=-a, j3=lean, j4=lean))]
        kf += [(0.6 * s, _pose(j3=lean, j4=lean)), (0.6 * s, HOME)]
    elif skill in ('point_left', 'point_right'):
        sign = 1.0 if skill == 'point_left' else -1.0
        yaw = sign * u(0.8, 1.3)
        sh = u(0.9, 1.3)
        kf = [(1.0 * s, _pose(j1=yaw, j2=sh, j3=0.2, j4=-0.2)),
              (u(0.3, 0.5), _pose(j1=yaw, j2=sh, j3=0.2, j4=-0.2)),
              (1.0 * s, HOME)]
    elif skill == 'grip':
        sh = u(0.6, 0.9)
        el = u(0.6, 0.9)
        wr = u(0.4, 0.7)
        reach = _pose(j2=sh, j3=el, j4=wr, g=GRIPPER_OPEN)
        grasp = _pose(j2=sh, j3=el, j4=wr, g=GRIPPER_CLOSE)
        lift = _pose(j2=0.3, j3=el, j4=wr, g=GRIPPER_CLOSE)
        kf = [(1.0 * s, reach), (0.6 * s, grasp), (0.8 * s, lift),
              (0.8 * s, _pose(g=GRIPPER_CLOSE)), (0.6 * s, HOME)]
    else:
        raise ValueError(f'unknown skill {skill}')
    return kf


def min_jerk(a, b, x):
    x = np.clip(x, 0.0, 1.0)
    w = 10 * x**3 - 15 * x**4 + 6 * x**5
    return a + (b - a) * w


def sample_trajectory(keyframes, dt=0.05, start=HOME):
    """Return array (N, 5) of targets sampled every dt seconds."""
    out = []
    cur = np.array(start, dtype=float)
    for dur, tgt in keyframes:
        n = max(1, int(round(dur / dt)))
        for i in range(1, n + 1):
            out.append(min_jerk(cur, tgt, i / n))
        cur = np.array(tgt, dtype=float)
    return np.array(out)


def final_pose(skill):
    return HOME.copy()
