#!/usr/bin/env python3
"""ACT training with CLI arguments (based on pai_training/scripts/train.py, Apache-2.0).

Additions: CLI args instead of a fixed yaml, GPU, loss log to CSV, wandb optional (offline).
  cd ~/pai_training && pixi run python /workspace/a_crane/scripts/train_act.py \
     --dataset-root ~/dataset/lerobot_dataset/bow_phase --repo-id bow_phase \
     --out ~/checkpoints/bow_phase --steps 4000
"""
import argparse
import csv
import time
from pathlib import Path

import numpy as np
import torch
from lerobot.common.datasets.lerobot_dataset import LeRobotDataset, LeRobotDatasetMetadata
from lerobot.common.datasets.utils import dataset_to_policy_features
from lerobot.common.policies.act.configuration_act import ACTConfig
from lerobot.common.policies.act.modeling_act import ACTPolicy
from lerobot.configs.types import FeatureType


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset-root', required=True)
    ap.add_argument('--repo-id', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--steps', type=int, default=4000)
    ap.add_argument('--batch-size', type=int, default=32)
    ap.add_argument('--lr', type=float, default=1e-4)
    ap.add_argument('--chunk-size', type=int, default=16)
    ap.add_argument('--device', default='cuda' if torch.cuda.is_available() else 'cpu')
    ap.add_argument('--model-size', choices=['small', 'default'], default='small',
                    help='small: dim 256 / ffn 1024 / 2 enc layers (the GPU is shared with other jobs)')
    ap.add_argument('--lag-aug', type=int, default=8, help='max observation lag in frames (0 = off)')
    ap.add_argument('--min-std', type=float, default=0.05, help='lower bound for normalisation std (rad)')
    ap.add_argument('--state-noise', type=float, default=0.0, help='Gaussian noise on observation.state (rad)')
    ap.add_argument('--check', action='store_true', help='compare the fast cache against LeRobotDataset[i]')
    args = ap.parse_args()

    if args.device == 'cpu':  # leave CPU for the Gazebo simulation running next to us
        import os
        torch.set_num_threads(int(os.environ.get('TORCH_THREADS', '4')))
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    root = Path(args.dataset_root).expanduser()
    meta = LeRobotDatasetMetadata(args.repo_id, root=root)
    feats = dataset_to_policy_features(meta.features)
    output_features = {k: f for k, f in feats.items() if f.type is FeatureType.ACTION}
    input_features = {k: f for k, f in feats.items()
                      if k in ('observation.state', 'observation.environment_state')}
    size = dict(small=dict(dim_model=256, dim_feedforward=1024, n_encoder_layers=2, n_vae_encoder_layers=2),
                default={})[args.model_size]
    cfg = ACTConfig(input_features=input_features, output_features=output_features,
                    chunk_size=args.chunk_size, n_action_steps=1, **size)
    # Joints that a skill never moves have std ~ 1e-6 in the dataset statistics; LeRobot divides by
    # (std + 1e-8), so a 0.001 rad wobble of such a joint in Gazebo becomes a ~1000-sigma input.
    # Clamp the std of every state/action dimension to >= min_std (rad).
    stats = meta.stats
    for key in ('observation.state', 'action'):
        std = np.asarray(stats[key]['std'], dtype=np.float32)
        stats[key]['std'] = np.maximum(std, args.min_std)
    policy = ACTPolicy(cfg, dataset_stats=stats)
    policy.train().to(args.device)

    # action chunk starts at the current frame: [0.0, 0.1, ..., 1.5] (lecture note)
    dts = {'observation.environment_state': [0.0], 'observation.state': [0.0],
           'action': [round(0.1 * i, 1) for i in range(args.chunk_size)]}
    # NOTE: frames are 0.05 s apart, the lecture config uses 0.1 s spacing -> chunk covers 1.5 s
    ds = LeRobotDataset(args.repo_id, root=root, delta_timestamps=dts)
    opt = torch.optim.Adam(policy.parameters(), lr=args.lr)
    # The datasets here are tiny (a few thousand frames): decode every sample once and keep
    # the whole dataset as tensors on the device. This avoids DataLoader worker re-spawning
    # every epoch, which made the lecture script ~10x slower in this container.
    t0 = time.time()
    # Build action chunks directly from the parquet columns (equivalent to delta_timestamps
    # [0.0, 0.1, ..., 1.5] with padding at the episode end), ~100x faster than ds[i].
    hf = ds.hf_dataset.with_format(None)
    col = lambda k: torch.tensor(np.array(hf[k]), dtype=torch.float32)
    st, es, act = col('observation.state'), col('observation.environment_state'), col('action')
    ep = torch.tensor(np.array(hf['episode_index']))
    step_frames = int(round(0.1 * meta.fps))
    offs = torch.arange(args.chunk_size) * step_frames
    idx = torch.arange(len(act))[:, None] + offs[None, :]
    idx_c = idx.clamp(max=len(act) - 1)
    pad = (idx >= len(act)) | (ep[idx_c] != ep[:, None])
    # padded positions repeat the last frame of the episode (like LeRobot), masked by action_is_pad
    last = torch.zeros_like(ep)
    for e in ep.unique():
        m = ep == e
        last[m] = torch.nonzero(m).max()
    idx_c = torch.where(pad, last[:, None].expand_as(idx_c), idx_c)
    cache = {'observation.state': st, 'observation.environment_state': es,
             'action': act[idx_c], 'action_is_pad': pad}
    # first frame index of each sample's episode (for lag augmentation)
    first = torch.zeros_like(ep)
    for e in ep.unique():
        m = ep == e
        first[m] = torch.nonzero(m).min()
    first = first.to(args.device)
    cache = {k: v.to(args.device) for k, v in cache.items()}
    if args.check:
        for i in torch.randint(0, len(act), (50,)).tolist():
            it = ds[i]
            assert torch.allclose(it["action"], cache["action"][i].cpu()), i
            assert torch.equal(it["action_is_pad"], cache["action_is_pad"][i].cpu()), i
        print("cache check ok", flush=True)
    n = cache['action'].shape[0]
    print(f'cached {n} samples in {time.time() - t0:.0f}s', flush=True)
    log = open(out / 'loss.csv', 'w', newline='')
    w = csv.writer(log)
    w.writerow(['step', 'loss', 'l1', 'kld', 'sec'])
    env_is_state = bool(torch.allclose(cache['observation.state'], cache['observation.environment_state']))
    print('environment_state == state:', env_is_state, flush=True)
    t0 = time.time()
    for step in range(args.steps):
        idx = torch.randint(0, n, (args.batch_size,), device=args.device)
        batch = {k: v[idx] for k, v in cache.items()}
        if args.lag_aug > 0:
            # Lag augmentation: observe the joint state of k frames earlier (k ~ U[0, lag_aug]) while the
            # target action stays the same -> the policy keeps following the skill's timeline even when the
            # simulated servos respond slower than during data collection.
            k = torch.randint(0, args.lag_aug + 1, (args.batch_size,), device=args.device)
            lagged = torch.maximum(idx - k, first[idx])
            batch['observation.state'] = cache['observation.state'][lagged]
        if args.state_noise > 0:
            batch['observation.state'] = batch['observation.state'] + args.state_noise * torch.randn_like(batch['observation.state'])
        if env_is_state:  # lecture setting: environment_state is a copy of the state
            batch['observation.environment_state'] = batch['observation.state']
        loss, info = policy.forward(batch)
        loss.backward()
        opt.step()
        opt.zero_grad()
        if step % 100 == 0 or step == args.steps - 1:
            w.writerow([step, f'{loss.item():.5f}', f"{info.get('l1_loss', 0):.5f}",
                        f"{info.get('kld_loss', 0):.5f}", f'{time.time() - t0:.1f}'])
            log.flush()
            print(f'step {step} loss {loss.item():.4f} ({time.time() - t0:.0f}s)', flush=True)
    policy.save_pretrained(out)
    import json
    env_mode = 'phasedq' if 'phasedq' in args.repo_id else ('phase' if 'phase' in args.repo_id else 'state')
    json.dump({'env_mode': env_mode, 'dataset': str(root), 'steps': args.steps,
               'batch_size': args.batch_size, 'model_size': args.model_size, 'lag_aug': args.lag_aug, 'state_noise': args.state_noise, 'min_std': args.min_std, 'chunk_size': args.chunk_size},
              open(out / 'a_crane_meta.json', 'w'), indent=1)
    print('saved', out, f'{time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
