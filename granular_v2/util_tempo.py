"""
Tempo and repeat utilities.

- expand_repeats_if_requested: expand DC/DS/Coda with cycle protection.
- build_seconds_map: quarter length -> seconds using metronome marks per section.

Tempo model (limitation): tempo changes are **stepwise** between successive
MetronomeMark boundaries. Accelerandi/ritardandi are approximated as plateaus,
not continuous BPM ramps. For most scores this is acceptable; document in thesis
if claiming micro-timing fidelity.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

import logging

from .offsets import boundary_ql as _boundary_offset

log = logging.getLogger(__name__)


def score_has_repeats(stream) -> bool:
    """Return True if the score contains repeat signs (DC, DS, Coda, etc.) that can be expanded."""
    try:
        from music21 import repeat

        check = stream
        if hasattr(stream, "parts") and stream.parts and not stream.hasMeasures():
            check = stream.parts[0]
        exp = repeat.Expander(check)
        return bool(exp.isExpandable())
    except Exception:
        return False


def _expand_stream_repeats(stream):
    from music21 import repeat

    exp = repeat.Expander(stream)
    return exp.process()


def expand_repeats_if_requested(stream, enabled: bool):
    """Expand repeats (DC, DS, Coda, etc.). On RecursionError (loop), return original."""
    if not enabled:
        return stream
    try:
        from music21 import repeat

        if hasattr(stream, "parts") and stream.parts and not stream.hasMeasures():
            expanded_parts = []
            for part in stream.parts:
                try:
                    expanded_parts.append(_expand_stream_repeats(part))
                except Exception as e:
                    log.warning(
                        "Repeat expansion failed for one part (%s). "
                        "If the score has only start-repeat barlines (no end-repeat :|), "
                        "add end-repeat barlines in the editor and re-export.",
                        e,
                    )
                    return stream
            out = stream.__class__()
            for attr in ("metadata", "id", "streamStatus"):
                if hasattr(stream, attr) and getattr(stream, attr, None) is not None:
                    try:
                        setattr(out, attr, getattr(stream, attr))
                    except Exception:
                        pass
            for p in expanded_parts:
                out.append(p)
            return out
        exp = repeat.Expander(stream)
        return exp.process()
    except RecursionError:
        log.warning("Repeat structure has a loop; using original score.")
        return stream
    except Exception as e:
        log.warning(
            "Repeat expansion failed: %s. Using original score. "
            "If the score has only start-repeat signs (|:) and no end-repeat (:|), add them and re-export.",
            e,
        )
        return stream


def build_seconds_map(stream) -> Callable[[float], float]:
    """
    Return ``ql_to_seconds(ql) -> seconds``.

    Stepwise tempo between MetronomeMark boundaries (see module docstring).
    On failure, a single global BPM is used. The callable has ``.tempo_info``:

        {"tempo_fallback_used": bool, "n_tempo_segments": int, "reason": str|None,
         "source": "metronomeMarkBoundaries" | "global_bpm_fallback"}
    """
    info: Dict[str, Any] = {
        "tempo_fallback_used": False,
        "n_tempo_segments": 0,
        "reason": None,
        "source": "metronomeMarkBoundaries",
    }
    try:
        bounds = stream.metronomeMarkBoundaries()
        if not bounds:
            raise ValueError("no metronome boundaries returned")
        segs = []
        t_sec = 0.0
        hi = float(stream.highestTime)
        for start_el, end_el, mm in bounds:
            q0 = _boundary_offset(start_el, 0.0)
            q1 = _boundary_offset(end_el, hi)
            bpm = float(getattr(mm, "number", None) or 120.0)
            segs.append((q0, q1, t_sec, bpm))
            t_sec += (60.0 / bpm) * (q1 - q0)
        info["n_tempo_segments"] = len(segs)
    except Exception as e:
        log.warning("metronomeMarkBoundaries failed (%s); using global BPM.", e)
        from music21 import tempo

        bpm = 120.0
        for m in stream.recurse().getElementsByClass(tempo.MetronomeMark):
            if getattr(m, "number", None) is not None:
                bpm = float(m.number)
                break
        segs = [(0.0, float(stream.highestTime), 0.0, bpm)]
        info["tempo_fallback_used"] = True
        info["n_tempo_segments"] = 1
        info["reason"] = f"metronomeMarkBoundaries failed: {e}; assumed {bpm:g} BPM"
        info["source"] = "global_bpm_fallback"

    def ql_to_seconds(q: float) -> float:
        for (q0, q1, s0, bpm) in segs:
            if q0 <= q < q1:
                return s0 + (60.0 / bpm) * (q - q0)
        q0, _q1, s0, bpm = segs[-1]
        return s0 + (60.0 / bpm) * (q - q0)

    ql_to_seconds.tempo_info = info  # type: ignore[attr-defined]
    return ql_to_seconds
