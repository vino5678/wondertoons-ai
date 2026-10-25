"""Scene duration arithmetic (pure functions).

Documented tolerance: the sum of scene durations must be within
max(2 seconds, 2% of the target) of the planned duration. The planner itself
allocates whole seconds that sum EXACTLY to the target; the tolerance exists
for user-edited scene plans.
"""
from __future__ import annotations

import math


def tolerance_seconds(target_seconds: int) -> float:
    return max(2.0, 0.02 * target_seconds)


def durations_within_tolerance(durations: list[int], target_seconds: int) -> bool:
    return abs(sum(durations) - target_seconds) <= tolerance_seconds(target_seconds)


def choose_scene_count(total_seconds: int, max_scenes: int, seconds_per_scene: int = 20) -> int:
    """About one scene per 20s, at least 2, never more than max_scenes or total seconds."""
    n = int((total_seconds + seconds_per_scene // 2) // seconds_per_scene)
    return max(2, min(n, max_scenes, total_seconds))


def allocate_durations(total_seconds: int, weights: list[float]) -> list[int]:
    """Split total_seconds into whole-second durations (each >= 1) proportional to
    weights, using largest-remainder rounding. The result sums exactly to total_seconds."""
    n = len(weights)
    if n == 0:
        raise ValueError("weights must not be empty")
    if any((not isinstance(w, (int, float))) or math.isnan(w) or math.isinf(w) or w <= 0 for w in weights):
        raise ValueError("weights must be positive finite numbers")
    if total_seconds < n:
        raise ValueError("total_seconds must be at least the number of scenes")
    spare = total_seconds - n
    total_w = float(sum(weights))
    raw = [spare * w / total_w for w in weights]
    floors = [int(math.floor(r)) for r in raw]
    leftover = spare - sum(floors)
    order = sorted(range(n), key=lambda i: (-(raw[i] - floors[i]), i))
    for i in order[:leftover]:
        floors[i] += 1
    return [1 + f for f in floors]
