"""
Score-global quarterLength offsets (music21 measure-local pitfall).

Use ``global_ql`` / ``global_offset`` for any element inside measures (notes, chords,
MetronomeMark). Use ``boundary_ql`` for metronomeMarkBoundaries() tuple endpoints
(which are plain floats, not Stream elements).
"""

from __future__ import annotations

from typing import Any


def global_offset(elem: Any, score: Any = None, part: Any = None, default: float = 0.0) -> float:
    """Alias for :func:`global_ql`."""
    return global_ql(elem, score=score, part=part, default=default)


def global_ql(el: Any, score: Any = None, part: Any = None, default: float = 0.0) -> float:
    """
    Score-global quarterLength position.

    ``el.offset`` restarts each measure; ``getOffsetInHierarchy`` resolves the true position.
    """
    if isinstance(el, (int, float)):
        return float(el)
    for ctx in (score, part):
        if ctx is None:
            continue
        try:
            return float(el.getOffsetInHierarchy(ctx))
        except Exception:
            continue
    off = getattr(el, "offset", None)
    return float(off) if off is not None else float(default)


def boundary_ql(elem: Any, default: float) -> float:
    """
    Quarter-length offset from a metronomeMarkBoundaries() boundary.

    Boundaries are ``(start_ql, end_ql, MetronomeMark)`` with plain floats — not Stream elements.
    """
    if elem is None:
        return float(default)
    if isinstance(elem, (int, float)):
        return float(elem)
    off = getattr(elem, "offset", None)
    return float(off) if off is not None else float(default)
