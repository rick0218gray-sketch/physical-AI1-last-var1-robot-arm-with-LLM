#!/usr/bin/env python3
"""Print the extreme value of each swing (sign segment with |x|>0.05) of one joint in runner CSVs.
usage: swing_peaks.py <column e.g. s_j1> file1.csv [file2.csv ...]"""
import csv
import sys
col = sys.argv[1]
for f in sys.argv[2:]:
    x = [float(r[col]) for r in csv.DictReader(open(f))]
    peaks, cur = [], None
    for v in x:
        if abs(v) < 0.05:
            continue
        s = v > 0
        if cur is None or s != cur[0]:
            cur = [s, v]
            peaks.append(cur)
        elif abs(v) > abs(cur[1]):
            cur[1] = v
    print(f.split('/')[-1], ' '.join(f'{p[1]:+.2f}' for p in peaks))
