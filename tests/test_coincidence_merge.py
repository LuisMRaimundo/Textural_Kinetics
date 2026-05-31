"""Mustextu coincidence merge — anchor-based grouping (no transitive chaining)."""

from granular_v2.mustextu.horizontal_density import _merge_coincident_onsets


def test_pair_only_realistic_ms():
    times, mult = _merge_coincident_onsets([0.0, 100.0, 100.5, 500.0], 2.0)
    assert times == [0.0, 100.25, 500.0]
    assert mult == [1, 2, 1]


def test_no_transitive_chain_across_ms():
    """[0, 1.5, 3.0, 4.5] ms tol 2 → two pairs, not one group of 4."""
    times, mult = _merge_coincident_onsets([0.0, 1.5, 3.0, 4.5], 2.0)
    assert mult == [2, 2]
    assert len(times) == 2
    assert abs(times[0] - 0.75) < 1e-9   # mean(0, 1.5)
    assert abs(times[1] - 3.75) < 1e-9   # mean(3, 4.5)


def test_double_onset_same_ms():
    times, mult = _merge_coincident_onsets([10.0, 10.0, 20.0], 1.0)
    assert mult == [2, 1]
    assert abs(times[0] - 10.0) < 1e-9
