#!/usr/bin/env python3
"""Open-loop probe: feed state=HOME and env=[t,0,0,0,0] for t = 0..3 s and print the first predicted action."""
import sys
import numpy as np
import torch
from lerobot.common.policies.act.modeling_act import ACTPolicy
p = ACTPolicy.from_pretrained(sys.argv[1]).eval().to('cpu')
home = torch.tensor([[0, 0, 0, 0, -0.5236]], dtype=torch.float32)
for t in np.arange(0, 3.01, 0.25):
    p.reset()
    a = p.select_action({'observation.state': home,
                         'observation.environment_state': torch.tensor([[t, 0, 0, 0, 0]], dtype=torch.float32)})
    print(f't={t:.2f} a={np.round(a.numpy().flatten(), 3)}')
