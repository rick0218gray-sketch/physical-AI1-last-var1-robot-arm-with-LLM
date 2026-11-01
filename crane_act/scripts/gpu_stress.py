#!/usr/bin/env python3
"""Load the GPU (and one CPU core) for N seconds to emulate the LLM running next to the policy."""
import sys
import time
import torch
end = time.time() + float(sys.argv[1])
x = torch.randn(4096, 4096, device='cuda')
while time.time() < end:
    for _ in range(20):
        y = x @ x
    torch.cuda.synchronize()
