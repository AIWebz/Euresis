"""Euresis-LM at 690 billion parameters — specification and resource requirements.

The configuration below uses exactly the same architecture and code as the
trained Euresis-LM (``euresis/lm/model.py``), scaled to 690.3 B parameters. The
parameter count is computed by tracing ``init_params`` abstractly
(``jax.eval_shape``), so no memory is allocated.

Such a model cannot be instantiated, let alone trained, on the machine Euresis
runs on (4 CPU cores, 15 GB RAM, no GPU): its weights alone are 1.4 TB in
bfloat16. ``requirements()`` states what training it would take.

    python -m euresis.lm.scale        # → space/lm_690b.md
"""
from __future__ import annotations

import math
from pathlib import Path

import jax
import jax.numpy as jnp

from .model import Config, forward, init_params, n_params

CONFIG_690B = Config(vocab=65536, ctx=4096, d=18432, layers=169, heads=144, mlp=4, dropout=0.0)

OUT = Path(__file__).resolve().parents[2] / "space" / "lm_690b.md"


def abstract_param_count(cfg: Config) -> int:
    shapes = jax.eval_shape(lambda k: init_params(cfg, k), jax.random.PRNGKey(0))
    return int(sum(math.prod(x.shape) for x in jax.tree_util.tree_leaves(shapes)))


def requirements(n: int, tokens_per_param: float = 20.0, gpu_flops: float = 989e12, mfu: float = 0.4,
                 gpu_mem_gb: float = 80.0) -> dict:
    """Compute-optimal (Chinchilla, ~20 tokens/parameter) training budget; H100-class GPUs at 40 % utilisation."""
    tokens = tokens_per_param * n
    flops = 6 * n * tokens
    gpu_seconds = flops / (gpu_flops * mfu)
    train_state_tb = n * 16 / 1e12                 # bf16 weights + fp32 master + Adam m, v + grads
    return {
        "parameters": n,
        "weights_bf16_tb": n * 2 / 1e12,
        "training_state_tb": train_state_tb,
        "min_gpus_to_hold_training_state": math.ceil(train_state_tb * 1e3 / gpu_mem_gb),
        "training_tokens": tokens,
        "training_flops": flops,
        "gpu_years": gpu_seconds / 3.15e7,
        "days_on_10k_gpus": gpu_seconds / 1e4 / 86400,
        "inference_gpus_bf16": math.ceil(n * 2 / 1e9 / gpu_mem_gb * 1.2),
    }


def smoke_test() -> dict:
    """The identical code path at 1/100 000 of the size: build, run a forward pass, check shapes."""
    cfg = Config(vocab=512, ctx=64, d=144, layers=2, heads=9, mlp=4)
    p = init_params(cfg, jax.random.PRNGKey(0))
    logits = forward(p, jnp.zeros((2, 16), jnp.int32), cfg)
    return {"params": n_params(p), "logits_shape": tuple(logits.shape), "finite": bool(jnp.isfinite(logits).all())}


def run(log=print) -> dict:
    n = abstract_param_count(CONFIG_690B)
    r = requirements(n)
    s = smoke_test()
    c = CONFIG_690B
    L = ["# Euresis-LM — 690 B parameter configuration", "",
         "Same architecture and code as the trained Euresis-LM (decoder-only transformer, `euresis/lm/model.py`), "
         "scaled up. The parameter count was computed by tracing the model's own `init_params` "
         "(`jax.eval_shape`, nothing allocated).", "",
         "| Setting | Value |", "|---|---|",
         f"| Parameters | **{n:,}** ({n / 1e9:.2f} B) |",
         f"| Layers | {c.layers} |", f"| Model width d | {c.d:,} |", f"| Attention heads | {c.heads} (head dim {c.d // c.heads}) |",
         f"| MLP width | {c.mlp * c.d:,} |", f"| Vocabulary | {c.vocab:,} |", f"| Context | {c.ctx:,} tokens |", "",
         "## What it would take", "",
         "| | |", "|---|---|",
         f"| Weights (bfloat16) | {r['weights_bf16_tb']:.2f} TB |",
         f"| Training state (weights, optimizer, gradients) | {r['training_state_tb']:.1f} TB → at least "
         f"{r['min_gpus_to_hold_training_state']} × 80 GB GPUs just to hold it |",
         f"| Compute-optimal training data | {r['training_tokens'] / 1e12:.1f} trillion tokens |",
         f"| Training compute | {r['training_flops']:.1e} FLOP |",
         f"| Time | ≈ {r['gpu_years']:,.0f} GPU-years (H100-class, 40 % utilisation) ≈ "
         f"{r['days_on_10k_gpus']:.0f} days on 10 000 GPUs |",
         f"| Serving it | ≈ {r['inference_gpus_bf16']} × 80 GB GPUs |", "",
         "## Status", "",
         "**Not trained, and not trainable here.** This machine has 4 CPU cores, 15 GB RAM, about 26 GB of free "
         "disk and no GPU; the weights alone would not fit on its disk. The text corpus Euresis has "
         "(≈ 200 k PubMed abstracts, tens of millions of tokens) is also about 10⁵–10⁶ × smaller than the "
         "≈ 14 trillion tokens such a model needs.", "",
         f"Smoke test of the identical code path at tiny scale: {s['params']:,} parameters, logits "
         f"{s['logits_shape']}, finite = {s['finite']}.", "",
         "Practical route to a model of this size: use an existing frontier model through its API as "
         "Euresis' reasoning core (Euresis already supports the Claude API — set `ANTHROPIC_API_KEY`).", ""]
    OUT.write_text("\n".join(L))
    log(f"690B config: {n:,} parameters; report → {OUT.relative_to(OUT.parents[1])}")
    return {"params": n, **r, "smoke": s}


if __name__ == "__main__":
    run()
