"""Bot random — baseline stupida ma valida."""
import random

ACTIONS = ["move_N", "move_S", "move_E", "move_W", "gather", "attack", "noop"]


def decide(obs: dict) -> dict:
    return {"action": random.choice(ACTIONS)}
