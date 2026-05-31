
# horizontal_density.py — v3
# See docstring in module for details.
from __future__ import annotations
import math, random, statistics
from typing import List, Dict, Tuple, Optional

def _lcm(a: int, b: int) -> int:
    from math import gcd
    return abs(a*b)//gcd(a,b) if a and b else 0
def _lcm_list(vals: List[int]) -> int:
    from functools import reduce
    return reduce(_lcm, vals, 1)
def _gcd_list(vals: List[int]) -> int:
    from math import gcd
    from functools import reduce
    return reduce(gcd, vals) if vals else 0

def _mk_onsets_regular(period_ms: float, window_ms: float, offset_ms: float = 0.0):
    if not math.isfinite(period_ms) or period_ms <= 0:
        return []
    offset_ms = float(offset_ms) % period_ms
    t = offset_ms
    onsets = []
    while t < window_ms:
        onsets.append(t)
        t += period_ms
    return onsets

def _rng_laplace(rng: random.Random, mu: float, b: float) -> float:
    u = rng.random() - 0.5
    if u == -0.5:
        # This edge case would cause math.log(0), which is undefined.
        # We can return a large value, which is consistent with the tail
        # of the Laplace distribution.
        return mu + b * 20  # A large, but finite value
    return mu - b * (1 if u < 0 else -1) * math.log(1 - 2*abs(u))

def _mk_onsets_irregular(period_ms: float, window_ms: float, offset_ms: float, jitter_ms: float,
                          rng: random.Random, jitter_mode: str = "gaussian"):
    base = _mk_onsets_regular(period_ms, window_ms, offset_ms)
    if jitter_ms <= 0 or not base:
        return base
    out = []
    for t in base:
        if jitter_mode == "uniform":
            jt = t + rng.uniform(-jitter_ms, jitter_ms)
        elif jitter_mode == "laplace":
            b = jitter_ms / (2**0.5)
            jt = t + _rng_laplace(rng, 0.0, b)
        else:
            jt = t + rng.gauss(0.0, jitter_ms)
        if 0.0 <= jt < window_ms:
            out.append(jt)
    return out

def _merge_coincident_onsets(onsets: List[float], coincidence_ms: float) -> Tuple[List[float], List[int]]:
    """
    Merge onsets within coincidence_ms of the group anchor (first onset in group).
    Compares to anchor, not to previous onset, to avoid transitive chaining.
    """
    if not onsets:
        return [], []
    onsets = sorted(onsets)
    merged_times, multiplicities = [], []
    current_group = [onsets[0]]
    anchor = onsets[0]
    for t in onsets[1:]:
        if (t - anchor) <= coincidence_ms:
            current_group.append(t)
        else:
            merged_times.append(sum(current_group) / len(current_group))
            multiplicities.append(len(current_group))
            current_group = [t]
            anchor = t
    merged_times.append(sum(current_group) / len(current_group))
    multiplicities.append(len(current_group))
    return merged_times, multiplicities

def compute_horizontal_density(
    bpm: float,
    window_ms: float,
    layers: List[Dict],
    iei_timbre_ms: float = 20.0,
    coincidence_ms: float = 2.0,
    adaptive_tolerance: bool = True,
    tol_frac_of_min_period: float = 0.05,
    align_window_to_beat: bool = True,
    gran_max_eps: float = 50.0,
    seed: Optional[int] = 1234,
    return_sequences: bool = True,
) -> Dict:
    if bpm <= 0: raise ValueError("bpm must be positive.")
    if window_ms <= 0: raise ValueError("window_ms must be positive.")
    if not layers: raise ValueError("At least one layer is required.")
    if coincidence_ms < 0: raise ValueError("coincidence_ms must be non-negative.")
    if gran_max_eps <= 0: raise ValueError("gran_max_eps must be positive.")

    rng = random.Random(seed) if seed is not None else random
    beat_ms = 60000.0 / bpm

    if align_window_to_beat:
        beats = max(1, round(window_ms / beat_ms))
        window_ms = beats * beat_ms

    per_layer = []
    all_onsets = []
    min_period = math.inf
    all_regular = True
    offsets_ok = True
    epb_ints = []

    for idx, L in enumerate(layers):
        name = str(L.get("name", "")) or f"Layer{idx+1}"
        epb = float(L.get("events_per_beat", 0.0))
        offset = float(L.get("offset_ms", 0.0))
        mode = (L.get("mode") or "regular").lower()
        jitter_ms = float(L.get("jitter_ms", 0.0))
        jitter_mode = (L.get("jitter_mode") or "gaussian").lower()

        if epb <= 0:
            period_ms = math.inf
            onsets = []
        else:
            period_ms = beat_ms / epb
            min_period = min(min_period, period_ms)
            if mode == "irregular":
                onsets = _mk_onsets_irregular(period_ms, window_ms, offset, jitter_ms, rng, jitter_mode=jitter_mode)
            else:
                onsets = _mk_onsets_regular(period_ms, window_ms, offset)

        events = len(onsets)
        rate_eps = (events / window_ms) * 1000.0 if window_ms > 0 else 0.0

        per_layer.append({
            "name": name, "mode": mode, "jitter_ms": jitter_ms if mode=="irregular" else 0.0,
            "jitter_mode": jitter_mode if mode=="irregular" else "",
            "events_per_beat": epb,
            "period_ms": float("inf") if not math.isfinite(period_ms) else period_ms,
            "events": events, "rate_eps": rate_eps, "offset_ms": offset,
        })
        all_onsets.extend(onsets)

        if mode != "regular" or not float(epb).is_integer():
            all_regular = False
        else:
            epb_ints.append(int(round(epb)))
            if abs(offset) > 1e-9:
                offsets_ok = False

    if adaptive_tolerance and math.isfinite(min_period):
        coincidence = max(0.0, min(coincidence_ms, tol_frac_of_min_period * min_period))
    else:
        coincidence = coincidence_ms

    all_onsets.sort()
    total_raw = len(all_onsets)

    merged_times, multiplicities = _merge_coincident_onsets(all_onsets, coincidence_ms=coincidence)
    total_unique = len(merged_times)

    ieis = [merged_times[i]-merged_times[i-1] for i in range(1, total_unique)] if total_unique>1 else []
    if ieis:
        s = sorted(ieis); n = len(s)
        iei_min = s[0]
        iei_median = s[n//2] if n%2==1 else 0.5*(s[n//2-1]+s[n//2])
        frac_timbre = sum(1 for v in s if v <= iei_timbre_ms) / n
    else:
        iei_min = float("inf"); iei_median = float("inf"); frac_timbre = 0.0

    rate_eps_raw = (total_raw / window_ms) * 1000.0 if window_ms > 0 else 0.0
    rate_eps_unique = (total_unique / window_ms) * 1000.0 if window_ms > 0 else 0.0

    g = max(0.0, min(1.0, rate_eps_unique / gran_max_eps))
    glabel = "fraca" if g < 0.33 else ("média" if g < 0.66 else "elevada")

    timbre_flag = (iei_median <= iei_timbre_ms) or (frac_timbre >= 0.5)

    coinc_groups = sum(1 for m in multiplicities if m >= 2)
    max_mult = max(multiplicities) if multiplicities else 0
    synchrony_fraction = 0.0 if total_raw == 0 else 1.0 - (total_unique / total_raw)
    avg_mult = 0.0 if total_unique == 0 else (total_raw / total_unique)
    excess_eps = rate_eps_raw - rate_eps_unique

    analytic = {}
    if all_regular and epb_ints:
        gcd_val = _gcd_list(epb_ints)
        lcm_val = _lcm_list(epb_ints)
        analytic = {
            "regular_case": True,
            "gcd_events_per_beat": gcd_val,
            "lcm_subdivisions_per_beat": lcm_val,
            "unique_per_beat_if_perfect_phase": sum(epb_ints) - gcd_val,
            "coincidences_per_beat_if_perfect_phase": gcd_val,
            "offsets_ok": offsets_ok
        }
    else:
        analytic = {"regular_case": False}

    out = {
        "per_layer": per_layer,
        "composite": {
            "bpm": bpm,
            "beat_ms": beat_ms,
            "window_ms": window_ms,
            "coincidence_ms_effective": coincidence,
            "params": {
                "iei_timbre_ms": iei_timbre_ms,
                "adaptive_tolerance": adaptive_tolerance,
                "tol_frac_of_min_period": tol_frac_of_min_period,
                "align_window_to_beat": align_window_to_beat,
                "gran_max_eps": gran_max_eps
            },
            "total_events_raw": total_raw,
            "total_events_unique": total_unique,
            "rate_eps_raw": rate_eps_raw,
            "rate_eps": rate_eps_unique,
            "excess_eps": excess_eps,
            "avg_multiplicity": avg_mult,
            "iei_min_ms": iei_min,
            "iei_median_ms": iei_median,
            "frac_IEI_le_thr": frac_timbre,
            "granularity_score": g,
            "granularity_label": glabel,
            "timbre_flag": timbre_flag,
            "timbre_rule": "median<=thr OR frac<=thr>=0.5",
            "synchrony_fraction": synchrony_fraction,
            "coincident_groups": coinc_groups,
            "max_multiplicity": max_mult,
            "analytic": analytic,
        }
    }
    if return_sequences:
        out["sequences"] = {"merged_times_ms": merged_times, "ieis_ms": ieis}
    return out

def _mean_std_ci(x: List[float]):
    if not x: return (float("nan"), float("nan"), (float("nan"), float("nan")))
    m = statistics.fmean(x)
    if len(x) == 1:
        return (m, float("nan"), (m, m))
    s = statistics.stdev(x)
    z = 1.96
    lo = m - z*(s/(len(x)**0.5)); hi = m + z*(s/(len(x)**0.5))
    return (m, s, (lo, hi))

def simulate_horizontal_density(
    bpm: float,
    window_ms: float,
    layers: List[Dict],
    iei_timbre_ms: float = 20.0,
    coincidence_ms: float = 2.0,
    adaptive_tolerance: bool = True,
    tol_frac_of_min_period: float = 0.05,
    align_window_to_beat: bool = True,
    gran_max_eps: float = 50.0,
    runs: int = 500,
    seed: int = 1234,
) -> Dict:
    metrics = {
        "total_events_unique": [], "rate_eps": [], "iei_median_ms": [],
        "granularity_score": [], "timbre_flag": [], "synchrony_fraction": [],
        "avg_multiplicity": [], "excess_eps": [], "frac_IEI_le_thr": []
    }
    for r in range(runs):
        res = compute_horizontal_density(
            bpm=bpm, window_ms=window_ms, layers=layers,
            iei_timbre_ms=iei_timbre_ms, coincidence_ms=coincidence_ms,
            adaptive_tolerance=adaptive_tolerance, tol_frac_of_min_period=tol_frac_of_min_period,
            align_window_to_beat=align_window_to_beat, gran_max_eps=gran_max_eps,
            seed=seed+r, return_sequences=False
        )
        comp = res["composite"]
        metrics["total_events_unique"].append(comp["total_events_unique"])
        metrics["rate_eps"].append(comp["rate_eps"])
        metrics["iei_median_ms"].append(comp["iei_median_ms"] if comp["iei_median_ms"]!=float("inf") else float("nan"))
        metrics["granularity_score"].append(comp["granularity_score"])
        metrics["timbre_flag"].append(1.0 if comp["timbre_flag"] else 0.0)
        metrics["synchrony_fraction"].append(comp["synchrony_fraction"])
        metrics["avg_multiplicity"].append(comp["avg_multiplicity"])
        metrics["excess_eps"].append(comp["excess_eps"])
        metrics["frac_IEI_le_thr"].append(comp["frac_IEI_le_thr"])

    summary = {}
    for k, arr in metrics.items():
        arr = [a for a in arr if not (isinstance(a,float) and math.isnan(a))]
        if not arr:
            summary[k] = {"mean": float("nan"), "std": float("nan"), "ci95_low": float("nan"), "ci95_high": float("nan")}
            continue
        m, s, (lo, hi) = _mean_std_ci(arr)
        summary[k] = {"mean": m, "std": s, "ci95_low": lo, "ci95_high": hi}
    summary["p_timbre"] = sum(metrics["timbre_flag"])/len(metrics["timbre_flag"]) if metrics["timbre_flag"] else float("nan")

    return {"runs": runs, "summary": summary}


# ======================
#  Real data (MusicXML/MIDI) support
# ======================
import os, io, tempfile
from xml.etree import ElementTree as ET
from typing import Iterable

def _load_mxml_any(path_or_stream):
    """
    Return (music21_stream, tmp_path_or_none).
    Accepts a filesystem path or a file-like (e.g., Streamlit UploadedFile).
    Does not consume the uploaded buffer permanently.
    """
    try:
        from music21 import converter
    except Exception as e:
        raise RuntimeError("music21 is required to parse MusicXML/MIDI") from e

    tmp = None
    if hasattr(path_or_stream, "read"):
        # Safely obtain bytes
        data = None
        try:
            data = path_or_stream.getvalue()
        except Exception:
            pass
        if data is None:
            try:
                path_or_stream.seek(0)
            except Exception:
                pass
            data = path_or_stream.read()
            try:
                path_or_stream.seek(0)
            except Exception:
                pass
        if not data:
            raise RuntimeError("Empty input data; could not read MusicXML/MIDI stream.")

        # First try parseData
        try:
            s = converter.parseData(data)
            return s, None
        except Exception:
            # Write to a temporary file (music21 is often more reliable with real paths)
            tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=".xml")
            tmpf.write(data); tmpf.flush(); tmpf.close()
            tmp = tmpf.name
            s = converter.parse(tmp)
            return s, tmp
    else:
        s = converter.parse(path_or_stream)
        return s, None

def _build_seconds_map_music21(s):
    """Delegate to package tempo map (global offsets + boundary floats)."""
    from ..timebase import build_tempo_segments
    from ..util_tempo import build_seconds_map

    fn = build_seconds_map(s)
    segs = build_tempo_segments(s)
    initial_bpm = float(segs[0].bpm) if segs else 120.0
    return fn, initial_bpm

def _is_grace(el) -> bool:
    try:
        if getattr(el, "quarterLength", None) == 0:
            return True
        d = getattr(el, "duration", None)
        return bool(getattr(d, "isGrace", False))
    except Exception:
        return False

def list_part_labels_from_musicxml(path_or_stream):
    """
    Robust listing of part labels.
    Tries music21; on failure, falls back to raw XML parsing of <score-part>.
    """
    # music21 route
    try:
        from music21 import stream
        s, tmp = _load_mxml_any(path_or_stream)
        try:
            parts = list(getattr(s, "parts", [])) or list(s.getElementsByClass(stream.Part))
            labels = []
            for p in parts:
                name = p.partName or ""
                if not name:
                    ins = p.getInstrument(returnDefault=False)
                    if ins and getattr(ins, "instrumentName", None):
                        name = ins.instrumentName
                labels.append(name or (p.id or "Part"))
            return labels
        finally:
            if tmp and os.path.exists(tmp):
                os.unlink(tmp)
    except Exception:
        # raw XML fallback
        try:
            if hasattr(path_or_stream, "getvalue"):
                data = path_or_stream.getvalue()
            elif hasattr(path_or_stream, "read"):
                try:
                    path_or_stream.seek(0)
                except Exception:
                    pass
                data = path_or_stream.read()
                try:
                    path_or_stream.seek(0)
                except Exception:
                    pass
            else:
                with open(path_or_stream, "rb") as fh:
                    data = fh.read()
            root = ET.fromstring(data)
            ns = ""
            if root.tag.startswith("{"):
                ns = root.tag.split("}")[0] + "}"
            labels = []
            for sp in root.findall(f".//{ns}score-part"):
                txt = ""
                el = sp.find(f"{ns}part-name")
                if el is not None and (el.text or "").strip():
                    txt = el.text.strip()
                if not txt:
                    el = sp.find(f"{ns}part-abbreviation")
                    if el is not None and (el.text or "").strip():
                        txt = el.text.strip()
                labels.append(txt or (sp.get("id") or "Part"))
            return labels
        except Exception as e:
            raise RuntimeError(f"Falha a ler partes (fallback XML): {e}")

def extract_onsets_per_layer_from_musicxml(path_or_stream, ignore_grace: bool = True,
                                           part_filter: Optional[Iterable[str]] = None) -> Tuple[dict, float, float]:
    """
    Parse MusicXML/MIDI, return (onsets_per_layer_ms, t_end_ms, initial_bpm).
    """
    try:
        from music21 import note, chord, stream
    except Exception as e:
        raise RuntimeError("music21 is required to parse MusicXML/MIDI") from e

    s, tmp = _load_mxml_any(path_or_stream)
    try:
        ql_to_s, initial_bpm = _build_seconds_map_music21(s)

        def _part_label(p: "stream.Part") -> str:
            name = p.partName or ""
            if not name:
                ins = p.getInstrument(returnDefault=False)
                if ins and getattr(ins, "instrumentName", None):
                    name = ins.instrumentName
            return name or (p.id or "Part")

        selected = set([x.strip() for x in part_filter]) if part_filter else None
        out = {}
        t_end_ms = 0.0

        from ..offsets import global_ql

        parts = list(getattr(s, "parts", [])) or list(s.getElementsByClass(stream.Part))
        for p in parts:
            label = _part_label(p)
            if selected and label not in selected:
                continue
            times = []
            for el in p.recurse().notesAndRests:
                if getattr(el, "isRest", False):
                    continue
                if ignore_grace and _is_grace(el):
                    continue
                q0 = global_ql(el, s, p)
                t0_ms = ql_to_s(q0) * 1000.0
                times.append(t0_ms)
                q1 = q0 + float(getattr(el, "quarterLength", 0.0) or 0.0)
                t1_ms = ql_to_s(q1) * 1000.0
                if t1_ms > t_end_ms:
                    t_end_ms = t1_ms
            if times:
                out[label] = sorted(times)

        return out, t_end_ms, initial_bpm
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)

def compute_horizontal_density_from_onsets(
    onsets_per_layer_ms: Dict[str, List[float]],
    window_ms: Optional[float] = None,
    iei_timbre_ms: float = 20.0,
    coincidence_ms: float = 2.0,
    adaptive_tolerance: bool = True,
    tol_frac_of_min_period: float = 0.05,
    align_window_to_beat: bool = False,
    bpm_for_alignment: Optional[float] = None,
    gran_max_eps: float = 50.0,
) -> Dict:
    """
    Compute horizontal density metrics from explicit onset times per layer (in ms).
    """
    if not onsets_per_layer_ms:
        raise ValueError("onsets_per_layer_ms cannot be empty.")

    # determine window
    if window_ms is None or window_ms <= 0:
        t_end = 0.0
        for ts in onsets_per_layer_ms.values():
            if ts:
                t_end = max(t_end, max(ts))
        window_ms = max(1.0, float(t_end))

    if align_window_to_beat and bpm_for_alignment and bpm_for_alignment > 0:
        beat_ms = 60000.0 / float(bpm_for_alignment)
        beats = max(1, round(window_ms / beat_ms))
        window_ms = beats * beat_ms
    else:
        beat_ms = None

    # estimate min period via per-layer median IEI
    min_period = math.inf
    per_layer = []
    all_onsets = []
    for name, times in onsets_per_layer_ms.items():
        ts = [t for t in times if 0.0 <= t < window_ms]
        ts.sort()
        ieis = [ts[i]-ts[i-1] for i in range(1, len(ts))] if len(ts) > 1 else []
        med_iei = float(statistics.median(ieis)) if ieis else float("inf")
        if math.isfinite(med_iei):
            min_period = min(min_period, med_iei)
        rate_eps = (len(ts) / window_ms) * 1000.0 if window_ms > 0 else 0.0
        per_layer.append({
            "name": str(name),
            "mode": "real",
            "events_per_beat": 0.0,
            "period_ms": med_iei,
            "events": len(ts),
            "rate_eps": rate_eps,
            "offset_ms": 0.0,
            "jitter_ms": 0.0,
            "jitter_mode": ""
        })
        all_onsets.extend(ts)

    coincidence = min(coincidence_ms, tol_frac_of_min_period * min_period) if (adaptive_tolerance and math.isfinite(min_period)) else coincidence_ms

    all_onsets.sort()
    total_raw = len(all_onsets)
    merged_times, multiplicities = _merge_coincident_onsets(all_onsets, coincidence_ms=coincidence)
    total_unique = len(merged_times)

    ieis = [merged_times[i]-merged_times[i-1] for i in range(1, total_unique)] if total_unique>1 else []
    if ieis:
        s = sorted(ieis); n = len(s)
        iei_min = s[0]
        iei_median = s[n//2] if n%2==1 else 0.5*(s[n//2-1]+s[n//2])
        frac_timbre = sum(1 for v in s if v <= iei_timbre_ms) / n
    else:
        iei_min = float("inf"); iei_median = float("inf"); frac_timbre = 0.0

    rate_eps_raw = (total_raw / window_ms) * 1000.0 if window_ms > 0 else 0.0
    rate_eps_unique = (total_unique / window_ms) * 1000.0 if window_ms > 0 else 0.0

    g = max(0.0, min(1.0, rate_eps_unique / gran_max_eps))
    glabel = "fraca" if g < 0.33 else ("média" if g < 0.66 else "elevada")
    timbre_flag = (iei_median <= iei_timbre_ms) or (frac_timbre >= 0.5)

    coinc_groups = sum(1 for m in multiplicities if m >= 2)
    max_mult = max(multiplicities) if multiplicities else 0
    synchrony_fraction = 0.0 if total_raw == 0 else 1.0 - (total_unique / total_raw)
    avg_mult = 0.0 if total_unique == 0 else (total_raw / total_unique)
    excess_eps = rate_eps_raw - rate_eps_unique

    composite = {
        "bpm": bpm_for_alignment if bpm_for_alignment else None,
        "beat_ms": (60000.0/float(bpm_for_alignment)) if bpm_for_alignment else None,
        "window_ms": window_ms,
        "coincidence_ms_effective": coincidence,
        "params": {
            "iei_timbre_ms": iei_timbre_ms,
            "adaptive_tolerance": adaptive_tolerance,
            "tol_frac_of_min_period": tol_frac_of_min_period,
            "align_window_to_beat": align_window_to_beat,
            "gran_max_eps": gran_max_eps
        },
        "total_events_raw": total_raw,
        "total_events_unique": total_unique,
        "rate_eps_raw": rate_eps_raw,
        "rate_eps": rate_eps_unique,
        "excess_eps": excess_eps,
        "avg_multiplicity": avg_mult,
        "iei_min_ms": iei_min,
        "iei_median_ms": iei_median,
        "frac_IEI_le_thr": frac_timbre,
        "granularity_score": g,
        "granularity_label": glabel,
        "timbre_flag": timbre_flag,
        "timbre_rule": "median<=thr OR frac<=thr>=0.5",
        "synchrony_fraction": synchrony_fraction,
        "coincident_groups": coinc_groups,
        "max_multiplicity": max_mult,
        "analytic": {"regular_case": False}
    }

    return {"per_layer": per_layer, "composite": composite, "sequences": {"merged_times_ms": merged_times, "ieis_ms": ieis}}

def compute_horizontal_density_from_musicxml(
    path_or_stream,
    window_ms: Optional[float] = None,
    part_filter: Optional[Iterable[str]] = None,
    iei_timbre_ms: float = 20.0,
    coincidence_ms: float = 2.0,
    adaptive_tolerance: bool = True,
    tol_frac_of_min_period: float = 0.05,
    align_window_to_beat: bool = True,
    gran_max_eps: float = 50.0,
    ignore_grace: bool = True,
) -> Dict:
    """
    Convenience wrapper: parse MusicXML/MIDI, extract onsets, and compute density.
    """
    onsets_per_layer, t_end_ms, initial_bpm = extract_onsets_per_layer_from_musicxml(
        path_or_stream, ignore_grace=ignore_grace, part_filter=part_filter
    )
    if window_ms is None or window_ms <= 0:
        window_ms = t_end_ms
    return compute_horizontal_density_from_onsets(
        onsets_per_layer_ms=onsets_per_layer,
        window_ms=window_ms,
        iei_timbre_ms=iei_timbre_ms,
        coincidence_ms=coincidence_ms,
        adaptive_tolerance=adaptive_tolerance,
        tol_frac_of_min_period=tol_frac_of_min_period,
        align_window_to_beat=align_window_to_beat,
        bpm_for_alignment=initial_bpm,
        gran_max_eps=gran_max_eps,
    )
