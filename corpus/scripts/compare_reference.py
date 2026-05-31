"""Regression: compare key metrics to reference JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from granular_v2.config import AnalysisConfig
from granular_v2.pipeline import run_analysis

FIXTURE = ROOT / "corpus" / "fixtures" / "sparse_homophony.musicxml"
REF = ROOT / "corpus" / "reference" / "sparse_homophony.json"
TOL = 1e-6


def main() -> int:
    if not FIXTURE.exists():
        FIXTURE_ALT = ROOT / "tests" / "fixtures" / "sample.musicxml"
        fixture = FIXTURE_ALT
        ref_path = ROOT / "corpus" / "reference" / "sample.json"
    else:
        fixture = FIXTURE
        ref_path = REF

    cfg = AnalysisConfig(enable_heatmaps=False, enable_mustextu=True)
    r = run_analysis(fixture, cfg, output_dir=None, export_json=False)

    if not ref_path.exists():
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        snap = {
            "num_events": r["num_events"],
            "events_per_second": r["event_rates"]["global"]["events_per_second"],
            "rate_eps": r.get("mustextu_summary", {}).get("rate_events_per_second"),
        }
        ref_path.write_text(json.dumps(snap, indent=2), encoding="utf-8")
        print("Wrote reference", ref_path)
        return 0

    ref = json.loads(ref_path.read_text(encoding="utf-8"))
    assert r["num_events"] == ref["num_events"], (r["num_events"], ref["num_events"])
    eps = r["event_rates"]["global"]["events_per_second"]
    assert abs(eps - ref["events_per_second"]) < TOL, (eps, ref["events_per_second"])
    if "rate_eps" in ref and r.get("mustextu_summary"):
        got = r["mustextu_summary"]["rate_events_per_second"]
        assert abs(got - ref["rate_eps"]) < 0.01, (got, ref["rate_eps"])
    print("compare_reference: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
