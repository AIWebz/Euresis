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
