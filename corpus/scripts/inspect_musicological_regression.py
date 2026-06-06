#!/usr/bin/env python3
"""Exploratory inspection report for musicological regression fixtures (phase 1)."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from granular_v2.activity_granularity import granularity_metrics
from granular_v2.config import AnalysisConfig
from granular_v2.loader import load_score_and_note_matrix
from granular_v2.note_extraction import extract_notes_with_ties
from granular_v2.onset_extraction import extract_onsets_per_layer_ms_from_score
from granular_v2.pipeline import run_analysis
from granular_v2.util_tempo import expand_repeats_if_requested

FIXTURE_DIR = ROOT / "corpus" / "fixtures" / "musicological_regression"
REPORT_DIR = ROOT / "corpus" / "reports"
REPORT_MD = REPORT_DIR / "musicological_regression_inspection.md"
REPORT_JSON = REPORT_DIR / "musicological_regression_inspection.json"


def _max_simultaneous_pitches(note_matrix) -> int:
    counts: dict[float, int] = defaultdict(int)
    for row in note_matrix:
        counts[round(float(row["onset_sec"]), 4)] += 1
    return max(counts.values()) if counts else 0


def _unique_onsets(note_matrix) -> int:
    return len({round(float(row["onset_sec"]), 4) for row in note_matrix})


def _inspect_fixture(path: Path) -> dict:
    name = path.stem
    row: dict = {"fixture": name, "path": str(path)}

    try:
        score, note_matrix, tempo_audit = load_score_and_note_matrix(path)
        row["load_ok"] = True
        row["num_events"] = len(note_matrix)
        row["tempo_audit"] = {
            "source": tempo_audit.get("source"),
            "tempo_fallback_used": tempo_audit.get("tempo_fallback_used"),
            "n_tempo_segments": tempo_audit.get("n_tempo_segments"),
            "warnings": tempo_audit.get("warnings", []),
        }
        if note_matrix:
            row["onset_min"] = min(float(n["onset_sec"]) for n in note_matrix)
            row["onset_max"] = max(float(n["onset_sec"]) for n in note_matrix)
            row["duration_min"] = min(float(n["duration_sec"]) for n in note_matrix)
            row["max_simultaneous_pitches"] = _max_simultaneous_pitches(note_matrix)
            row["unique_onsets"] = _unique_onsets(note_matrix)
            row["granularity"] = granularity_metrics(note_matrix)
        else:
            row["onset_min"] = None
            row["onset_max"] = None
            row["duration_min"] = None
            row["max_simultaneous_pitches"] = 0
            row["unique_onsets"] = 0
            row["granularity"] = {}

        cfg = AnalysisConfig(enable_heatmaps=False, enable_mustextu=True)
        results = run_analysis(path, cfg, output_dir=None, export_json=False)
        row["events_per_second"] = results["event_rates"]["global"]["events_per_second"]
        must = results.get("mustextu_summary") or {}
        row["mustextu"] = {
            "synchrony_fraction": must.get("synchrony_fraction"),
            "rate_events_per_second": must.get("rate_events_per_second"),
            "granularity_score": must.get("granularity_score"),
        }

        if name == "tied_sustained_texture":
            _, raw, _ = load_score_and_note_matrix(path, merge_ties=False)
            row["tied_compare"] = {
                "merged_events": len(note_matrix),
                "raw_events": len(raw),
                "merged_unique_onsets": _unique_onsets(note_matrix),
                "raw_unique_onsets": _unique_onsets(raw),
            }

        if name == "repeated_section" and score is not None:
            expanded = expand_repeats_if_requested(score, True)
            row["repeat_compare"] = {
                "events_before": len(extract_notes_with_ties(score)),
                "events_after": len(extract_notes_with_ties(expanded)),
            }

        if name == "grace_note_passage" and score is not None:
            onsets_ignore, _, _, _ = extract_onsets_per_layer_ms_from_score(
                score, ignore_grace=True
            )
            onsets_include, _, _, _ = extract_onsets_per_layer_ms_from_score(
                score, ignore_grace=False
            )
            row["grace_compare"] = {
                "onsets_ignore_grace": sum(len(v) for v in onsets_ignore.values()),
                "onsets_include_grace": sum(len(v) for v in onsets_include.values()),
            }

        if name == "transposing_instrument_score":
            _, written, _ = load_score_and_note_matrix(path, pitch_domain="written")
            _, sounding, _ = load_score_and_note_matrix(path, pitch_domain="sounding")
            row["transposition_compare"] = {
                "written_pitches": [int(n["pitch"]) for n in written],
                "sounding_pitches": [int(n["pitch"]) for n in sounding],
                "written_onsets": [float(n["onset_sec"]) for n in written],
                "sounding_onsets": [float(n["onset_sec"]) for n in sounding],
            }

        if name == "tempo_change_mid_score" and note_matrix:
            onsets = sorted({round(float(n["onset_sec"]), 3) for n in note_matrix})
            iois = [round(onsets[i + 1] - onsets[i], 3) for i in range(len(onsets) - 1)]
            row["tempo_iois"] = iois

    except Exception as exc:
        row["load_ok"] = False
        row["error"] = repr(exc)

    return row


def _render_markdown(rows: list[dict]) -> str:
    lines = [
        "# Musicological regression — exploratory inspection",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "Phase 1 report. Values are **exploratory** — not locked golden references.",
        "",
        "| Fixture | Events | Unique onsets | Max simultaneous | Sync fraction | EPS global | IOI CV |",
        "|---------|-------:|--------------:|-----------------:|--------------:|-----------:|-------:|",
    ]
    for row in rows:
        g = row.get("granularity") or {}
        must = row.get("mustextu") or {}
        ioi_cv = g.get("ioi_cv")
        ioi_txt = f"{ioi_cv:.4f}" if isinstance(ioi_cv, (int, float)) else "—"
        sync = must.get("synchrony_fraction")
        sync_txt = f"{sync:.3f}" if isinstance(sync, (int, float)) else "—"
        eps = row.get("events_per_second")
        eps_txt = f"{eps:.4f}" if isinstance(eps, (int, float)) else "—"
        lines.append(
            f"| {row['fixture']} | {row.get('num_events', '—')} | "
            f"{row.get('unique_onsets', '—')} | {row.get('max_simultaneous_pitches', '—')} | "
            f"{sync_txt} | {eps_txt} | {ioi_txt} |"
        )

    lines.extend(["", "## Per-fixture notes", ""])
    for row in rows:
        lines.append(f"### `{row['fixture']}`")
        if not row.get("load_ok"):
            lines.append(f"- **Load failed:** `{row.get('error')}`")
            lines.append("")
            continue
        audit = row.get("tempo_audit") or {}
        lines.append(f"- Tempo source: `{audit.get('source')}`; segments: `{audit.get('n_tempo_segments')}`")
        if row.get("tied_compare"):
            tc = row["tied_compare"]
            lines.append(
                f"- Tie merge: raw `{tc['raw_events']}` / merged `{tc['merged_events']}` events; "
                f"unique onsets raw `{tc['raw_unique_onsets']}` → merged `{tc['merged_unique_onsets']}`"
            )
        if row.get("repeat_compare"):
            rc = row["repeat_compare"]
            lines.append(f"- Repeat expansion: `{rc['events_before']}` → `{rc['events_after']}` events")
        if row.get("grace_compare"):
            gc = row["grace_compare"]
            lines.append(
                f"- Grace onsets: ignore `{gc['onsets_ignore_grace']}`, include `{gc['onsets_include_grace']}`"
            )
        if row.get("transposition_compare"):
            tc = row["transposition_compare"]
            lines.append(f"- Written pitches: `{tc['written_pitches']}`")
            lines.append(f"- Sounding pitches: `{tc['sounding_pitches']}`")
        if row.get("tempo_iois"):
            lines.append(f"- Unique-onset IOIs (sec): `{row['tempo_iois']}`")
        lines.append("")

    lines.append(
        "> Review these values before promoting any to `corpus/reference/` golden files."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    fixtures = sorted(FIXTURE_DIR.glob("*.musicxml"))
    if not fixtures:
        print(f"No fixtures in {FIXTURE_DIR}. Run create_musicological_regression_fixtures.py first.")
        return 1

    rows = [_inspect_fixture(path) for path in fixtures]
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(rows), encoding="utf-8")
    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
