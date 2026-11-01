#!/usr/bin/env python3
"""Sanity check of the success criteria: apply eval_traj.evaluate to the scripted demonstrations.
usage (pixi env): python eval_demos.py <skill> <dataset_root> [n_episodes]"""
import csv
import glob
import os
import sys
import tempfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_traj import evaluate  # noqa: E402

skill, root = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 10
files = sorted(glob.glob(f'{root}/data/chunk-000/episode_*.parquet'))[:n]
ok = 0
for f in files:
    s = np.stack(pd.read_parquet(f)['observation.state'].values)
    with tempfile.NamedTemporaryFile('w', suffix='.csv', delete=False, newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['t', 's_j1', 's_j2', 's_j4', 's_j3', 's_g'])
        for i, r in enumerate(s):
            w.writerow([i * 0.05] + r.tolist())
    r = evaluate(skill, fh.name)
    ok += r[0]
    os.unlink(fh.name)
print(f'{skill}: demos passing the success criterion {ok}/{len(files)}')
