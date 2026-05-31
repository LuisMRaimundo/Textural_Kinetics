# Granularity Analyser (Granular_v2 v1.0.5)

Fused symbolic analyzer combining **Granularidade** (Mustextu, spectral heatmap) and **Densidade horizontal_v3** (activity density, dual heatmaps, partitional option).

## Precise event rates

| Metric | Unit | Definition |
|--------|------|------------|
| `events_per_second` | 1/s | N / (last_onset − first_onset) in seconds |
| `events_per_millisecond` | 1/ms | `events_per_second / 1000` |
| `events_per_millisecond_in_window` | 1/ms | onsets in window / window_ms |
| `events_per_second_in_bar` | 1/s | onsets in measure / measure duration (s) |
| `events_per_beat_in_bar` | 1/beat | onsets in measure / notated beats |
| `rate_events_per_second` (Mustextu) | 1/s | unique onsets / window (after coincidence merge) |

All exported in `analysis.json` under `event_rates` with unit definitions.

## Heatmaps (3 PNGs)

- `heatmap_basic.png` — time × pitch (log counts)
- `heatmap_advanced.png` — smoothed, note names, measure lines
- `heatmap_spectral.png` — velocity-weighted grid (symbolic, not audio)

## Install

```bash
pip install -e ".[dev,full]"
```

## CLI

```bash
python -m granular_v2.run score.musicxml -o out
python -m granular_v2.run score.musicxml -o out --no-heatmaps --partitional
```

## API

```python
from granular_v2 import run_analysis, default_analysis_config

result = run_analysis("score.musicxml", default_analysis_config(), output_dir="out")
print(result["event_rates"]["global"]["events_per_second"])
print(result["mustextu_summary"]["rate_events_per_second"])
```

## GUI

```bash
python -m granular_v2.gui
```

Windows: `run_gui.bat`

## Tests & regression

```bash
pytest tests -q
python corpus/scripts/compare_all.py
```

Corpus fixtures: `corpus/fixtures/*.musicxml` (from Granularidade synthetic scores).

## Scope

Symbolic notation only. See `export_metadata` in JSON output.
