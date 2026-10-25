from app.core.durations import (allocate_durations, choose_scene_count, durations_within_tolerance,
                                tolerance_seconds)


def test_allocation_sums_exactly():
    for total in (10, 33, 60, 61, 599, 3600):
        for weights in ([1, 2, 1.2, 0.8], [1, 1, 1], [5, 1], [1.0] * 7):
            if total >= len(weights):
                d = allocate_durations(total, weights)
                assert sum(d) == total and all(x >= 1 for x in d)


def test_allocation_is_proportional_and_deterministic():
    assert allocate_durations(60, [1, 2, 1]) == allocate_durations(60, [1, 2, 1])
    d = allocate_durations(60, [1, 2, 1])
    assert d[1] > d[0] and d[1] > d[2]


def test_allocation_rejects_bad_input():
    for bad in ([], [0, 1], [-1, 2], [float("nan"), 1]):
        try:
            allocate_durations(30, bad)
        except ValueError:
            continue
        raise AssertionError(f"accepted {bad}")
    try:
        allocate_durations(2, [1, 1, 1])
    except ValueError:
        pass
    else:
        raise AssertionError("accepted total < scenes")


def test_tolerance():
    assert tolerance_seconds(60) == 2.0
    assert tolerance_seconds(3600) == 72.0
    assert durations_within_tolerance([20, 20, 21], 60)
    assert not durations_within_tolerance([20, 20, 25], 60)


def test_scene_count_bounds():
    assert choose_scene_count(10, 200) == 2
    assert choose_scene_count(60, 200) == 3
    assert choose_scene_count(3600, 200) == 180
    assert choose_scene_count(3600, 50) == 50
