# Offset audit manifest (Textural_Kinetics)

## Root cause

In music21, `element.offset` inside a measure is **measure-local** (restarts at 0 each bar).
Timeline code must use `getOffsetInHierarchy(score|part)` via `granular_v2.offsets.global_ql`.

## Textural_Kinetics — audited modules (v1.0.5+; release 1.0.6)

| Module | Role | Status |
|--------|------|--------|
| `offsets.py` | Canonical helpers | Source of truth |
| `timebase.py` | Tempo segments | Fixed |
| `note_extraction.py` | Note matrix QL onsets | Fixed |
| `onset_extraction.py` | Mustextu onsets (ms) | Fixed |
| `util_tempo.py` | `metronomeMarkBoundaries` | `boundary_ql` for floats |
| `loader.py` | Orchestration + `tempo_audit.warnings` | Fixed |
| `input_layer.py` | MusicXML + MIDI load | MIDI fallback uses `global_ql` |
| `mustextu/horizontal_density.py` | Legacy XML path | Delegates to package tempo + `global_ql` |
| `measures.py` | Measure `m.offset` in **part** stream | OK (cumulative bar position in part) |

## Tests

- `tests/test_global_offsets_integration.py` — synthetic 2-bar 2-tempo file round-trip
- `tests/test_offset_audit.py` — corpus invariants + static guard + Mustextu alignment

## Sibling tools (not in this repo path — manual follow-up)

| Project | Files still using raw `.offset` |
|---------|----------------------------------|
| Granularidade | `utils/timebase.py`, `processors.py`, `modules/heatmap.py`, `modules/spectrum.py`, `modules/dynamics.py` |
| Densidade horizontal_v3 | `timebase.py`, `note_extraction.py`, `input_layer.py`, `dynamics.py` |

Port the `offsets.py` pattern before trusting multi-measure rates in those tools.

## Real repertoire

`corpus/fixtures/*.musicxml` are exported scores (not programmatic stubs). Add more
exports from thesis corpus as they are cleared for redistribution; re-run
`corpus/scripts/compare_all.py` to refresh references.
