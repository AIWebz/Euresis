"""Discovery across subjects beyond mathematics and physics.

    music theory   theorems about scales and chords        proof by exhaustion (all 4096 pitch-class sets)
    economics      sharp bounds in Cournot competition,    Z3 proof over the model's parameter space
                   insurance under risk aversion, auctions (runs inside `physics-discover2`)
    linguistics    statistical laws of written language    found on one corpus, confirmed on a held-out one
    game theory    complete solutions of octal games       Guy–Smith periodicity theorem

Every claim goes through the verification gate and into the claims registry.
"""
from __future__ import annotations

from . import games, linguistics, music
from .registry import Registry


def run(max_game_digits: int = 3, game_minutes: float = 30, echo=print) -> dict:
    reg = Registry()
    out = {}
    echo("== music theory (proof by exhaustion)")
    st = music.run(reg, echo=echo)
    out["music"] = {"discoveries": len(st["discoveries"]), "rediscoveries": len(st["rediscoveries"])}
    echo("== linguistics (held-out replication)")
    st = linguistics.run(reg, echo=echo)
    out["linguistics"] = {"findings": len(st["discoveries"]), "rediscoveries": len(st["rediscoveries"])}
    echo("== game theory (Guy–Smith periodicity theorem)")
    st = games.run(max_digits=max_game_digits, reg=reg, echo=echo, max_minutes=game_minutes)
    out["games"] = {"solved": len(st["solved"]), "unresolved": len(st["unresolved"])}
    echo("== economics runs inside the two-variable engine: python -m euresis physics-discover2")
    echo(str(out))
    return out


def run_segment(minutes: float = 100, echo=print) -> dict:
    """One time-boxed segment of the open-ended search (call repeatedly; state is saved between segments):
    extend music theory to the next equal temperament, then keep solving octal games (4 digits)."""
    import json
    import time
    from . import music_n
    t0 = time.time()
    reg = Registry()
    st = json.loads(music_n.STATE.read_text()) if music_n.STATE.exists() else {"n_max_done": 0}
    nxt = max(music_n.N_MAX, st.get("n_max_done", 0) + 1)
    if nxt <= 18:
        echo(f"== music theory: extending to {music_n.N_MIN}–{nxt}-note equal temperaments")
        music_n.run(reg, echo=echo, n_max=nxt)
    left = minutes - (time.time() - t0) / 60
    if left > 1:
        gst = json.loads(games.STATE.read_text()) if games.STATE.exists() else {"done": []}
        done = set(gst["done"])
        digits = next((d for d in (3, 4, 5, 6) if any(c not in done for c in games.codes(d))), 6)
        echo(f"== game theory: octal games up to {digits} digits ({left:.0f} min)")
        games.run(max_digits=digits, N=3000, reg=reg, echo=echo, max_minutes=left)
    return {"minutes": round((time.time() - t0) / 60, 1)}
