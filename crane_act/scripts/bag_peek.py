#!/usr/bin/env python3
"""Print a coarse summary of a recorded episode (system ROS python)."""
import sys
import rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message

r = rosbag2_py.SequentialReader()
r.open(rosbag2_py.StorageOptions(uri=sys.argv[1], storage_id='sqlite3'),
       rosbag2_py.ConverterOptions('cdr', 'cdr'))
types = {t.name: t.type for t in r.get_all_topics_and_types()}
t0 = None
k = {}
while r.has_next():
    topic, data, t = r.read_next()
    t0 = t0 or t
    k[topic] = k.get(topic, 0) + 1
    if k[topic] % 10 != 1:
        continue
    m = deserialize_message(data, get_message(types[topic]))
    if topic == '/joint_states':
        print(f'{(t-t0)/1e9:6.2f} JS ', [round(x, 2) for x in m.position])
    elif 'arm' in topic:
        print(f'{(t-t0)/1e9:6.2f} ARM', [round(x, 2) for x in m.points[0].positions])
