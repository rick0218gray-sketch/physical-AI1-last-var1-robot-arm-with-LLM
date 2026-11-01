#!/usr/bin/env python3
"""Run pai_training/scripts/debug_policy.py unchanged, but save the GT-vs-pred plot to --png
instead of opening a window.  usage: debug_policy_save.py --png out.png <debug_policy args...>"""
import runpy
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

i = sys.argv.index('--png')
png = sys.argv[i + 1]
del sys.argv[i:i + 2]
plt.show = lambda *a, **k: plt.savefig(png, dpi=100)
import os
sys.argv[0] = os.path.join(os.environ.get('PAI_TRAINING_ROOT', os.path.expanduser('~/pai_training')), 'scripts', 'debug_policy.py')
runpy.run_path(sys.argv[0], run_name='__main__')
