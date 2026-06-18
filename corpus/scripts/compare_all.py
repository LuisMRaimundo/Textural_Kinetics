"""Regression across all corpus/fixtures/*.musicxml."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from granular_v2.config import AnalysisConfig
from granular_v2.pipeline import run_analysis

FIX_DIR = ROOT / "corpus" / "fixtures"
REF_DIR = ROOT / "corpus" / "reference"
TOL = 1e-5
TOL_MUSTEXTU = 0.02


def _snapshot(r):
    return {
        "num_events": r["event_rates"]["global"]["num_events"],
        "num_notes": r["num_events"],
        "events_per_second": r["event_rates"]["global"]["events_per_second"],
        "rate_eps": r.get("mustextu_summary", {}).get("rate_events_per_second"),
    }


def main() -> int:
    REF_DIR.mkdir(parents=True, exist_ok=True)
    fixtures = sorted(FIX_DIR.glob("*.musicxml"))
    if not fixtures:
        fixtures = sorted((ROOT / "tests" / "fixtures").glob("*.musicxml"))
    if not fixtures:
        print("No fixtures found")
        return 1

    cfg = AnalysisConfig(enable_heatmaps=False, enable_mustextu=True)
    failed = []
    for fx in fixtures:
        name = fx.stem
        ref_path = REF_DIR / f"{name}.json"
        r = run_analysis(fx, cfg, output_dir=None, export_json=False)
        snap = _snapshot(r)
        if not ref_path.exists():
            ref_path.write_text(json.dumps(snap, indent=2), encoding="utf-8")
            print(f"Wrote {ref_path.name}")
            continue
        ref = json.loads(ref_path.read_text(encoding="utf-8"))
        try:
            assert snap["num_events"] == ref["num_events"]
            assert abs(snap["events_per_second"] - ref["events_per_second"]) < TOL
            if ref.get("rate_eps") is not None and snap.get("rate_eps") is not None:
                assert abs(snap["rate_eps"] - ref["rate_eps"]) < TOL_MUSTEXTU
            print(f"OK {name}")
        except AssertionError as e:
            failed.append((name, snap, ref, str(e)))
    if failed:
        for name, snap, ref, err in failed:
            print(f"FAIL {name}: {err}\n  got={snap}\n  ref={ref}")
        return 1
    print(f"compare_all: {len(fixtures)} fixtures OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
