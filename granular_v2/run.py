from __future__ import annotations

import argparse
from pathlib import Path

from .config import AnalysisConfig, default_analysis_config
from .pipeline import run_analysis


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Textural_Kinetics — fused symbolic temporal-density analysis")
    p.add_argument("score", type=Path)
    p.add_argument("-o", "--output-dir", type=Path, default=Path("out"))
    p.add_argument("--no-heatmaps", action="store_true")
    p.add_argument("--no-mustextu", action="store_true")
    p.add_argument("--partitional", action="store_true")
    p.add_argument("--intervals", default="0.1,0.5,1.0", help="Density bin widths (seconds)")
    args = p.parse_args(argv)

    intervals = [float(x.strip()) for x in args.intervals.split(",") if x.strip()]
    cfg = default_analysis_config()
    cfg.density_intervals = intervals
    cfg.enable_heatmaps = not args.no_heatmaps
    cfg.enable_mustextu = not args.no_mustextu
    cfg.include_partitional = args.partitional

    r = run_analysis(args.score, cfg, output_dir=args.output_dir)
    g = r["event_rates"]["global"]
    print("Events:", r["num_events"])
    print("events_per_second:", g["events_per_second"])
    print("events_per_millisecond:", g["events_per_millisecond"])
    if r.get("mustextu_summary"):
        m = r["mustextu_summary"]
        print("Mustextu rate_events_per_second:", m["rate_events_per_second"])
    if r.get("heatmap_paths"):
        for k, v in r["heatmap_paths"].items():
            print(f"  {k}: {v}")
    print("JSON:", Path(args.output_dir) / "analysis.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
