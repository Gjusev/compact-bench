"""Mock navigation tasks: deterministic grid world with walls and items."""

from .base import Task

_GRID = 6
_DELTAS = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}


class GridEnv:
    """6x6 grid, coordinates (x, y), start (0, 0). Deterministic."""

    def __init__(self, walls, goal, items):
        self.walls = frozenset(walls)
        self.goal = goal
        self.items = frozenset(items)
        self.pos = (0, 0)
        self.collected = frozenset()
        self.finished = False

    def execute(self, action: str) -> str:
        parts = action.split()
        if len(parts) == 2 and parts[0] == "move" and parts[1] in _DELTAS:
            dx, dy = _DELTAS[parts[1]]
            nx, ny = self.pos[0] + dx, self.pos[1] + dy
            if not (0 <= nx < _GRID and 0 <= ny < _GRID) or (nx, ny) in self.walls:
                return "BUMPED WALL position=(%d,%d)" % self.pos
            self.pos = (nx, ny)
            obs = ["position=(%d,%d)" % self.pos]
            if self.pos in self.items and self.pos not in self.collected:
                self.collected = self.collected | {self.pos}
                obs.append("collected item at (%d,%d)" % self.pos)
            if self.pos == self.goal:
                obs.append("GOAL REACHED")
            return "; ".join(obs)
        return "UNKNOWN ACTION: %s" % action[:40]


def _nav_check(env, answer):
    ok = env.pos == env.goal and env.collected == env.items and bool(answer)
    return ok, "pos=%s collected=%s answer=%r" % (
        env.pos, sorted(env.collected), answer,
    )


def _make(name, prompt, plan, walls, goal, items):
    return Task(
        name=name,
        category="nav",
        prompt=prompt,
        plan=plan,
        build_env=lambda: GridEnv(walls, goal, items),
        check=_nav_check,
    )


_PROMPT = (
    "GRID WORLD: 6x6, you start at (0,0); x grows East, y grows South.\n"
    "Task: reach the goal square%s Steps you may take:\n"
    '- "move N|S|E|W" moves one square (bumps report a wall),\n'
    '- "finish: <answer>" submits once the goal is reached.\n'
    "The observation tells you your position after every move."
)

ALL_NAV_TASKS = [
    _make(
        "nav-corridor",
        _PROMPT % " at (4,0).",
        ("move E", "move E", "move E", "move E", "finish: reached (4,0)"),
        walls=(),
        goal=(4, 0),
        items=(),
    ),
    _make(
        "nav-around-wall",
        _PROMPT % " at (4,0); there is a wall blocking the direct route.",
        (
            "move S", "move S", "move E", "move E", "move E",
            "move N", "move N", "move E", "finish: reached (4,0) around the wall",
        ),
        walls=((2, 0), (2, 1)),
        goal=(4, 0),
        items=(),
    ),
    _make(
        "nav-collect",
        _PROMPT % " at (4,3) after collecting BOTH items.",
        (
            "move E", "move E", "move S", "move S", "move S",
            "move E", "move E", "finish: reached (4,3) with both items",
        ),
        walls=((1, 1),),
        goal=(4, 3),
        items=((2, 0), (2, 3)),
    ),
]
