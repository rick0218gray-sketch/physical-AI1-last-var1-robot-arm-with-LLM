#!/usr/bin/env python3
"""Thin client for skill_server.py.  skill_client.py <skill|__ping__> [seconds]
exit 0: skill finished, 1: server error, 4: server not reachable"""
import json
import os
import socket
import sys

port = int(os.environ.get('SKILL_SERVER_PORT', '9877'))
skill = sys.argv[1]
req = {'skill': '__list__' if skill == '__ping__' else skill}
if len(sys.argv) > 2 and sys.argv[2]:
    req['seconds'] = float(sys.argv[2])
if os.environ.get('START_MARKER'):
    req['start_marker'] = os.environ['START_MARKER']
    req['start_delay'] = float(os.environ.get('START_DELAY', '0'))
try:
    s = socket.create_connection(('127.0.0.1', port), timeout=3)
except OSError:
    print('skill server not reachable')
    sys.exit(4)
s.settimeout(300)
s.sendall((json.dumps(req) + '\n').encode())
resp = json.loads(s.makefile().readline())
if not resp.get('ok'):
    print('error:', resp.get('error'))
    sys.exit(1)
if skill == '__ping__':
    print('skill server running, skills:', ', '.join(resp['skills']))
else:
    # same "wall=" field as the one-shot path: seconds of visible motion, ending at this line
    print(f"done: {resp['skill']} {resp['seconds']}s home_reached={resp['home_reached']} wall={resp.get('wall', 0):.2f}s",
          flush=True)
    print('log:', resp['log'])
    print(resp['eval'])
