#!/usr/bin/env python3
"""Automatic demonstration generator for CRANE+ V2 (replaces keyboard teleop).

Publishes JointTrajectory commands in exactly the same format as
physicalai_teleop (20 Hz, one point, time_from_start=0.1 s, arm joint order
joint1, joint2, joint4, joint3) and wraps every episode in its own
`ros2 bag record` process.

usage: python3 auto_demo.py --skill bow --episodes 30 --out ~/dataset/rosbags/bow --seed 0
"""
import argparse
import os
import signal
import subprocess
import sys
import threading
import time

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skills  # noqa: E402

ARM_JOINT_NAMES = ['crane_plus_joint1', 'crane_plus_joint2', 'crane_plus_joint4', 'crane_plus_joint3']
GRIPPER_JOINT_NAME = 'crane_plus_joint_hand'
TOPICS = ['/joint_states', '/crane_plus_arm_controller/joint_trajectory',
          '/crane_plus_gripper_controller/joint_trajectory']
DT = 0.05


def to_cmd_order(q):
    """semantic [j1,j2,j3,j4] -> command order [j1,j2,j4,j3]"""
    return [float(q[0]), float(q[1]), float(q[3]), float(q[2])]


class AutoDemo(Node):
    def __init__(self):
        super().__init__('crane_plus_auto_demo', parameter_overrides=[
            Parameter('use_sim_time', Parameter.Type.BOOL, os.environ.get('SIM_TIME', '0') == '1')])
        self.arm_pub = self.create_publisher(JointTrajectory, '/crane_plus_arm_controller/joint_trajectory', 10)
        self.gripper_pub = self.create_publisher(JointTrajectory, '/crane_plus_gripper_controller/joint_trajectory', 10)
        self.create_subscription(JointState, '/joint_states', self._js_cb, 10)
        self.target = skills.HOME.copy()
        self.lock = threading.Lock()
        self.js = None
        self.create_timer(DT, self._publish)

    def _js_cb(self, msg):
        d = dict(zip(msg.name, msg.position))
        self.js = np.array([d.get('crane_plus_joint1', 0.0), d.get('crane_plus_joint2', 0.0),
                            d.get('crane_plus_joint3', 0.0), d.get('crane_plus_joint4', 0.0),
                            d.get(GRIPPER_JOINT_NAME, 0.0)])

    def set_target(self, q):
        with self.lock:
            self.target = np.array(q, dtype=float)

    def _publish(self):
        with self.lock:
            q = self.target.copy()
        jt = JointTrajectory()
        jt.joint_names = ARM_JOINT_NAMES
        pt = JointTrajectoryPoint()
        pt.positions = to_cmd_order(q[:4])
        pt.time_from_start.nanosec = int(0.1 * 1e9)
        jt.points.append(pt)
        self.arm_pub.publish(jt)
        jg = JointTrajectory()
        jg.joint_names = [GRIPPER_JOINT_NAME]
        pg = JointTrajectoryPoint()
        pg.positions = [float(q[4])]
        pg.time_from_start.nanosec = int(0.1 * 1e9)
        jg.points.append(pg)
        self.gripper_pub.publish(jg)


def wait_home(node, timeout=8.0, tol=0.03):
    node.set_target(skills.HOME)
    t0 = time.time()
    while time.time() - t0 < timeout:
        if node.js is not None and np.max(np.abs(node.js - skills.HOME)) < tol:
            return True
        time.sleep(0.1)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--skill', required=True)
    ap.add_argument('--episodes', type=int, default=30)
    ap.add_argument('--out', required=True)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--start-index', type=int, default=0)
    ap.add_argument('--pre', type=float, default=0.2, help='seconds at HOME before motion (recorded)')
    ap.add_argument('--post', type=float, default=0.5, help='seconds at HOME after motion (recorded)')
    args = ap.parse_args()

    rclpy.init()
    node = AutoDemo()
    th = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    th.start()
    rng = np.random.default_rng(args.seed)
    out = os.path.expanduser(args.out)
    os.makedirs(out, exist_ok=True)
    time.sleep(1.0)
    print('homing...', wait_home(node, 15.0), flush=True)

    for ep in range(args.start_index, args.start_index + args.episodes):
        kf = skills.make_keyframes(args.skill, rng)
        traj = skills.sample_trajectory(kf, DT)
        ok = wait_home(node)
        time.sleep(0.5)
        bag = os.path.join(out, f'ep_{ep:03d}')
        if os.path.exists(bag):
            subprocess.run(['rm', '-rf', bag])
        rec = subprocess.Popen(['ros2', 'bag', 'record', '-o', bag] + TOPICS,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               preexec_fn=os.setsid)
        # wait until the recorder has actually opened its database, then a margin
        for _ in range(100):
            if os.path.isdir(bag) and any(f.endswith('.db3') for f in os.listdir(bag)):
                break
            time.sleep(0.1)
        time.sleep(0.7)
        time.sleep(args.pre)
        t0 = time.time()
        sim = lambda: node.get_clock().now().nanoseconds * 1e-9
        s0 = sim()
        for i, q in enumerate(traj):
            node.set_target(q)
            if os.environ.get('SIM_TIME', '0') == '1':
                # v3: step the scripted trajectory on the SIMULATION clock -> the tempo in sim time is
                # independent of the real-time factor (which varied 0.55-0.92 while other jobs ran)
                while sim() < s0 + (i + 1) * DT:
                    time.sleep(0.002)
                continue
            # absolute timing to avoid drift
            delay = t0 + (i + 1) * DT - time.time()
            if delay > 0:
                time.sleep(delay)
        node.set_target(skills.HOME)
        t1 = time.time()
        while time.time() - t1 < 4.0:  # let the arm settle at HOME (still recording)
            if node.js is not None and np.max(np.abs(node.js - skills.HOME)) < 0.03:
                break
            time.sleep(0.05)
        time.sleep(args.post)
        os.killpg(os.getpgid(rec.pid), signal.SIGINT)
        try:
            rec.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(rec.pid), signal.SIGKILL)
        err = None if node.js is None else float(np.max(np.abs(node.js - skills.HOME)))
        print(f'[{args.skill}] ep {ep:03d} len={len(traj) * DT:.2f}s home_ok_before={ok} '
              f'end_err={err}', flush=True)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
