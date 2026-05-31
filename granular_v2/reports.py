"""Export metadata and JSON helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .config import AnalysisConfig

SCOPE = [
    "Symbolic MusicXML/MIDI analysis only",
    "Event rates: per second, per millisecond, per bar, Mustextu rate_eps",
    "Heatmaps: symbolic pitch-time (not measured audio)",
]

NOT_CLAIMED = [
    "Acoustic STFT / psychoacoustic validation",
    "Full Gentil-Nunes PARSEMAT equivalence",
]


def export_metadata(config: AnalysisConfig) -> Dict[str, Any]:
    return {
        "scope": SCOPE,
        "not_claimed": NOT_CLAIMED,
        "merge_ties": config.merge_ties,
        "pitch_domain": config.pitch_domain,
        "density_intervals": list(config.density_intervals),
        "enable_mustextu": config.enable_mustextu,
        "enable_heatmaps": config.enable_heatmaps,
        "include_partitional": config.include_partitional,
    }


def export_results_json(results: Dict[str, Any], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
