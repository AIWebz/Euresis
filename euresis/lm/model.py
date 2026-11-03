"""Euresis-LM: a GPT-style transformer language model, written from scratch in JAX.

Architecture: token + learned position embeddings → N pre-LayerNorm decoder
blocks (causal multi-head self-attention, GELU MLP, residuals) → final
LayerNorm → output projection tied to the token embedding. Byte-level BPE
tokenizer trained on Euresis' own corpus. Trained with AdamW, cosine schedule.

Uses inside Euresis:
* ``rank(question, candidates)`` — scores how likely each candidate (a law name)
  is as the answer, i.e. language understanding for the mystery solver;
* ``generate(prompt)`` — writes text (explanations, answers).
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import jax
import jax.numpy as jnp
import numpy as np
import optax

MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "euresis-lm"


@dataclass
class Config:
    vocab: int = 4096
    ctx: int = 128
    d: int = 256
    layers: int = 6
    heads: int = 8
    mlp: int = 4
    dropout: float = 0.0


def init_params(cfg: Config, key):
    ks = iter(jax.random.split(key, 4 + cfg.layers * 4))
    s = 0.02
    p = {"tok": jax.random.normal(next(ks), (cfg.vocab, cfg.d)) * s,
         "pos": jax.random.normal(next(ks), (cfg.ctx, cfg.d)) * s,
         "lnf_g": jnp.ones(cfg.d), "lnf_b": jnp.zeros(cfg.d), "blocks": []}
    proj_s = s / math.sqrt(2 * cfg.layers)
    for _ in range(cfg.layers):
        p["blocks"].append({
            "ln1_g": jnp.ones(cfg.d), "ln1_b": jnp.zeros(cfg.d),
            "qkv": jax.random.normal(next(ks), (cfg.d, 3 * cfg.d)) * s, "qkv_b": jnp.zeros(3 * cfg.d),
            "o": jax.random.normal(next(ks), (cfg.d, cfg.d)) * proj_s, "o_b": jnp.zeros(cfg.d),
            "ln2_g": jnp.ones(cfg.d), "ln2_b": jnp.zeros(cfg.d),
            "fc": jax.random.normal(next(ks), (cfg.d, cfg.mlp * cfg.d)) * s, "fc_b": jnp.zeros(cfg.mlp * cfg.d),
            "pr": jax.random.normal(next(ks), (cfg.mlp * cfg.d, cfg.d)) * proj_s, "pr_b": jnp.zeros(cfg.d)})
    return p


def _ln(x, g, b, eps=1e-5):
    m = x.mean(-1, keepdims=True)
    v = ((x - m) ** 2).mean(-1, keepdims=True)
    return (x - m) / jnp.sqrt(v + eps) * g + b


def forward(params, idx, cfg: Config):
    """idx: (B, T) int tokens → logits (B, T, vocab)."""
    B, T = idx.shape
    x = params["tok"][idx] + params["pos"][:T]
    mask = jnp.tril(jnp.ones((T, T), bool))
    hd = cfg.d // cfg.heads
    for blk in params["blocks"]:
        h = _ln(x, blk["ln1_g"], blk["ln1_b"])
        q, k, v = jnp.split(h @ blk["qkv"] + blk["qkv_b"], 3, axis=-1)
        q, k, v = (t.reshape(B, T, cfg.heads, hd).transpose(0, 2, 1, 3) for t in (q, k, v))
        att = (q @ k.transpose(0, 1, 3, 2)) / math.sqrt(hd)
        att = jnp.where(mask, att, -1e9)
        att = jax.nn.softmax(att, axis=-1)
        y = (att @ v).transpose(0, 2, 1, 3).reshape(B, T, cfg.d)
        x = x + y @ blk["o"] + blk["o_b"]
        h = _ln(x, blk["ln2_g"], blk["ln2_b"])
        x = x + jax.nn.gelu(h @ blk["fc"] + blk["fc_b"]) @ blk["pr"] + blk["pr_b"]
    x = _ln(x, params["lnf_g"], params["lnf_b"])
    return x @ params["tok"].T


def n_params(params) -> int:
    return int(sum(x.size for x in jax.tree_util.tree_leaves(params)))


# ------------------------------------------------------------------ tokenizer
def train_tokenizer(texts, vocab_size):
    from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers
    tok = Tokenizer(models.BPE())
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tok.decoder = decoders.ByteLevel()
    trainer = trainers.BpeTrainer(vocab_size=vocab_size, special_tokens=["<|eos|>"],
                                  initial_alphabet=pre_tokenizers.ByteLevel.alphabet())
    tok.train_from_iterator(texts, trainer)
    return tok


# -------------------------------------------------------------------- model
class EuresisLM:
    def __init__(self, params, cfg: Config, tokenizer):
        self.params, self.cfg, self.tok = params, cfg, tokenizer
        self.eos = tokenizer.token_to_id("<|eos|>")
        self._fwd = jax.jit(lambda p, x: forward(p, x, cfg))

    # ----------------------------------------------------------- training
    @classmethod
    def train(cls, docs, cfg: Config | None = None, steps=3000, batch=32, lr=3e-3, seed=0, log=print,
              out_dir: Path = MODEL_DIR, init_from: Path | None = None):
        """init_from: continue from an existing model (fine-tuning) — reuses its tokenizer and weights."""
        if init_from is not None:
            base = cls.load(init_from)
            cfg = base.cfg
            out_dir.mkdir(parents=True, exist_ok=True)
            base.tok.save(str(out_dir / "tokenizer.json"))
            eos_id = base.tok.token_to_id("<|eos|>")
            enc = base.tok.encode_batch(docs)
            np.save(out_dir / "corpus_tokens.npy",
                    np.fromiter((i for e in enc for i in (e.ids + [eos_id])), dtype=np.int32))
        cfg = cfg or Config()
        out_dir.mkdir(parents=True, exist_ok=True)
        tok_path, data_path = out_dir / "tokenizer.json", out_dir / "corpus_tokens.npy"
        if tok_path.exists() and data_path.exists():          # cached: skip tokenizer training and encoding
            from tokenizers import Tokenizer
            tok = Tokenizer.from_file(str(tok_path))
            data = np.load(data_path)
            log("loaded cached tokenizer and tokenised corpus")
        else:
            tok = train_tokenizer(docs, cfg.vocab)
            tok.save(str(tok_path))
            eos_id = tok.token_to_id("<|eos|>")
            enc = tok.encode_batch(docs)                       # parallel encoding
            data = np.fromiter((i for e in enc for i in (e.ids + [eos_id])), dtype=np.int32)
            np.save(data_path, data)
        cfg.vocab = tok.get_vocab_size()
        eos = tok.token_to_id("<|eos|>")
        n_val = len(data) // 20
        train_d, val_d = data[:-n_val], data[-n_val:]
        log(f"corpus: {len(data):,} tokens (vocab {cfg.vocab}); training {steps} steps × {batch}×{cfg.ctx} tokens")
        params = base.params if init_from is not None else init_params(cfg, jax.random.PRNGKey(seed))
        log(f"model: {n_params(params):,} parameters, {cfg.layers} layers, d={cfg.d}, {cfg.heads} heads")
        sched = optax.warmup_cosine_decay_schedule(0.0, lr, min(200, steps // 10), steps, lr * 0.05)
        opt = optax.chain(optax.clip_by_global_norm(1.0), optax.adamw(sched, b1=0.9, b2=0.95, weight_decay=0.05))
        state = opt.init(params)

        def loss_fn(p, x, y):
            logits = forward(p, x, cfg)
            return optax.softmax_cross_entropy_with_integer_labels(logits, y).mean()

        @jax.jit
        def step(p, s, x, y):
            l, g = jax.value_and_grad(loss_fn)(p, x, y)
            upd, s = opt.update(g, s, p)
            return optax.apply_updates(p, upd), s, l

        eval_loss = jax.jit(loss_fn)
        rng = np.random.default_rng(seed)

        def sample(d):
            ix = rng.integers(0, len(d) - cfg.ctx - 1, batch)
            x = np.stack([d[i:i + cfg.ctx] for i in ix])
            y = np.stack([d[i + 1:i + cfg.ctx + 1] for i in ix])
            return jnp.array(x), jnp.array(y)
        hist = []
        t0 = time.time()
        vrng = np.random.default_rng(seed + 1)
        vix = vrng.integers(0, len(val_d) - cfg.ctx - 1, 128)
        VX = jnp.array(np.stack([val_d[i:i + cfg.ctx] for i in vix]))
        VY = jnp.array(np.stack([val_d[i + 1:i + cfg.ctx + 1] for i in vix]))
        best = (float("inf"), params, 0)
        start = 1
        ckpt = out_dir / "checkpoint.npz"
        if ckpt.exists():                                       # resume after an interruption
            z = np.load(ckpt, allow_pickle=False)
            pflat, ptree = jax.tree_util.tree_flatten(params)
            sflat, stree = jax.tree_util.tree_flatten(state)
            params = jax.tree_util.tree_unflatten(ptree, [jnp.array(z[f"p{i}"]) for i in range(len(pflat))])
            state = jax.tree_util.tree_unflatten(stree, [jnp.array(z[f"s{i}"]) for i in range(len(sflat))])
            bflat = [jnp.array(z[f"b{i}"]) for i in range(len(pflat))]
            best = (float(z["best_val"]), jax.tree_util.tree_unflatten(ptree, bflat), int(z["best_step"]))
            start = int(z["step"]) + 1
            hist = json.loads(str(z["hist"]))
            rng = np.random.default_rng(seed + start)
            log(f"resuming from checkpoint at step {start - 1}")

        def save_ckpt(it):
            arrs = {f"p{i}": np.asarray(a) for i, a in enumerate(jax.tree_util.tree_leaves(params))}
            arrs.update({f"s{i}": np.asarray(a) for i, a in enumerate(jax.tree_util.tree_leaves(state))})
            arrs.update({f"b{i}": np.asarray(a) for i, a in enumerate(jax.tree_util.tree_leaves(best[1]))})
            tmp = out_dir / "checkpoint.tmp.npz"
            np.savez(tmp, step=it, best_val=best[0], best_step=best[2], hist=json.dumps(hist), **arrs)
            tmp.replace(ckpt)

        for it in range(start, steps + 1):
            x, y = sample(train_d)
            params, state, l = step(params, state, x, y)
            if it % 100 == 0:
                save_ckpt(it)
            if it % 100 == 0 or it == 1:
                vl = float(np.mean([float(eval_loss(params, VX[i:i + 32], VY[i:i + 32])) for i in range(0, 128, 32)]))
                hist.append({"step": it, "train_loss": float(l), "val_loss": vl})
                mark = ""
                if vl < best[0]:
                    best = (vl, params, it)
                    mark = "  <- best"
                log(f"  step {it:5d}  train {float(l):.3f}  val {vl:.3f}  ({time.time() - t0:.0f}s){mark}")
        log(f"keeping the checkpoint with the lowest held-out loss: step {best[2]} (val {best[0]:.3f})")
        m = cls(best[1], cfg, tok)
        m.save(out_dir, {"history": hist, "tokens": int(len(data)), "parameters": n_params(params),
                         "best_step": best[2], "best_val_loss": best[0], "train_seconds": round(time.time() - t0)})
        if ckpt.exists():
            ckpt.unlink()
        return m

    def save(self, out_dir: Path, meta=None):
        out_dir.mkdir(parents=True, exist_ok=True)
        flat, tree = jax.tree_util.tree_flatten(self.params)
        np.savez(out_dir / "params.npz", *[np.asarray(a) for a in flat])
        (out_dir / "config.json").write_text(json.dumps(asdict(self.cfg)))
        self.tok.save(str(out_dir / "tokenizer.json"))
        if meta:
            (out_dir / "training.json").write_text(json.dumps(meta, indent=1))

    @classmethod
    def load(cls, out_dir: Path = MODEL_DIR):
        from tokenizers import Tokenizer
        cfg = Config(**json.loads((out_dir / "config.json").read_text()))
        template = init_params(cfg, jax.random.PRNGKey(0))
        _, tree = jax.tree_util.tree_flatten(template)
        z = np.load(out_dir / "params.npz")
        params = jax.tree_util.tree_unflatten(tree, [jnp.array(z[f"arr_{i}"]) for i in range(len(z.files))])
        return cls(params, cfg, Tokenizer.from_file(str(out_dir / "tokenizer.json")))

    @staticmethod
    def available(out_dir: Path = MODEL_DIR) -> bool:
        return (out_dir / "params.npz").exists()

    # ---------------------------------------------------------- inference
    def logprob(self, prefix: str, continuations: list[str], batch=64) -> np.ndarray:
        """Mean log-probability per token of each continuation given the prefix."""
        pre = self.tok.encode(prefix).ids
        seqs = [pre + self.tok.encode(c).ids + [self.eos] for c in continuations]
        out = np.zeros(len(seqs))
        L = min(self.cfg.ctx, max(len(s) for s in seqs))
        for i in range(0, len(seqs), batch):
            chunk = seqs[i:i + batch]
            arr = np.zeros((len(chunk), L), np.int32)
            for j, s in enumerate(chunk):
                s = s[-L:]
                arr[j, :len(s)] = s
            lp = jax.nn.log_softmax(self._fwd(self.params, jnp.array(arr)), -1)
            lp = np.asarray(lp)
            for j, s in enumerate(chunk):
                s = s[-L:]
                start = max(1, len(s) - (len(s) - len(pre)))
                tgt = range(start, len(s))
                out[i + j] = np.mean([lp[j, t - 1, s[t]] for t in tgt]) if len(s) > start else -1e9
        return out

    def rank(self, question: str, candidates: list[str], prompt="question: {q}\nlaw:") -> list[tuple[str, float]]:
        # byte-level BPE attaches the space to the following word, exactly as in training text
        scores = self.logprob(prompt.format(q=question), [" " + c for c in candidates])
        order = np.argsort(-scores)
        return [(candidates[i], float(scores[i])) for i in order]

    def generate(self, prompt: str, max_new=80, temperature=0.7, top_k=40, seed=0) -> str:
        rng = np.random.default_rng(seed)
        ids = self.tok.encode(prompt).ids
        for _ in range(max_new):
            ctx = np.array([ids[-self.cfg.ctx:]], np.int32)
            logits = np.asarray(self._fwd(self.params, jnp.array(ctx)))[0, -1] / max(temperature, 1e-6)
            if top_k:
                kth = np.sort(logits)[-top_k]
                logits = np.where(logits < kth, -1e9, logits)
            p = np.exp(logits - logits.max())
            p /= p.sum()
            nxt = int(rng.choice(len(p), p=p))
            if nxt == self.eos:
                break
            ids.append(nxt)
        return self.tok.decode(ids)[len(prompt):] if self.tok.decode(ids).startswith(prompt) else self.tok.decode(ids)
