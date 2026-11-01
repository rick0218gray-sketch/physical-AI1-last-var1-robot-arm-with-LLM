#!/usr/bin/env python3
"""Log /joint_states for N wall seconds to a CSV in the skill_runner format (for evaluating
policies that are run by other programs, e.g. the lecture's `pixi run infer`)."""
import csv
import sys
import time
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

ORDER = ['crane_plus_joint1', 'crane_plus_joint2', 'crane_plus_joint4', 'crane_plus_joint3', 'crane_plus_joint_hand']
rclpy.init()
n = Node('js_logger')
rows = []
t0 = time.time()
n.create_subscription(JointState, '/joint_states',
                      lambda m: rows.append([round(time.time() - t0, 3)] +
                                            [dict(zip(m.name, m.position))[k] for k in ORDER] + [0] * 5), 10)
end = t0 + float(sys.argv[2])
while time.time() < end:
    rclpy.spin_once(n, timeout_sec=0.05)
with open(sys.argv[1], 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['t'] + [f's_{k}' for k in ('j1', 'j2', 'j4', 'j3', 'g')] + [f'a_{k}' for k in ('j1', 'j2', 'j4', 'j3', 'g')])
    w.writerows(rows)
