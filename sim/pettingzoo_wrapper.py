"""Adapter PettingZoo Parallel API sopra il sim Botcraft — cablaggio, core intoccato.

Uso (quando pettingzoo è installato, altrimenti duck-typing puro):
    from sim.pettingzoo_wrapper import BotcraftParallel
    env = BotcraftParallel(seed=1)
    obs = env.reset()
    while not env.done:
        obs, rewards, done = env.step({"p1": {"action": "gather"}, "p2": {"action": "noop"}})
Così CleanRL/Tianshou/SuperSuit possono trattare Botcraft come un env qualunque.
"""
from __future__ import annotations
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from sim.sim import new_match, step, to_obs, result


class BotcraftParallel:
    agents = ("p1", "p2")

    def __init__(self, seed: int = 1):
        self.seed = seed
        self.state = new_match(seed)
        self.done = False

    def reset(self, seed: int | None = None):
        if seed is not None:
            self.seed = seed
        self.state = new_match(self.seed)
        self.done = False
        return {a: to_obs(self.state, i) for i, a in enumerate(self.agents)}

    def step(self, actions: dict):
        a1 = actions.get("p1", {"action": "noop"})
        a2 = actions.get("p2", {"action": "noop"})
        step(self.state, a1, a2)
        obs = {a: to_obs(self.state, i) for i, a in enumerate(self.agents)}
        res = result(self.state)
        self.done = bool(self.state["over"])
        rewards = {"p1": res["s0"], "p2": res["s1"]} if self.done else {"p1": 0, "p2": 0}
        return obs, rewards, self.done

    def observe(self, agent: str):
        return to_obs(self.state, 0 if agent == "p1" else 1)
