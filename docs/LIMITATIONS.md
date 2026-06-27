# Granular_v2 — documented limitations

## Tempo → seconds (stepwise model)

`build_seconds_map` and `timebase.build_tempo_segments` treat tempo as **piecewise constant** between successive `MetronomeMark` entries. Accelerandi, ritardandi, and other continuous tempo curves are approximated as plateaus. Event rates in seconds are therefore tied to notated metronome marks, not to performance timing.

## Symbolic analysis only

Heatmaps and “spectral” grids are **notation-based** (pitch × time, velocity-weighted). They do not represent measured audio spectra or psychoacoustic loudness.

Scalar metrics (EPS global, IOI CV, synchrony fraction, burstiness) are likewise **score-derived model outputs**, not perceptual measures. VD4 IOI CV / granularity index / burstiness use **fused onsets** (τ = 2 ms); raw diagnostics and Mustextu rates are documented separately. See **[METRIC_SEMANTICS.md](METRIC_SEMANTICS.md)**.

## Mustextu coincidence merge

Onsets within `coincidence_ms` of a group **anchor** are merged. This avoids transitive chaining across distant onsets (fixed in v1.0.1).

## Partitional layer

Optional partition indices are simplified (channel-based); not a complete partitional formalism.

## VD10 registral trajectory

- **User-defined block:** the tool does not auto-detect voices or textural layers; spans are manual picks on the heatmap.
- **Separate from granularity:** high event rate does not imply registral motion; a registral round-trip can yield **net_speed ≈ 0** while `total_path` is large.
- **Semitone resolution:** picks snap to integer MIDI pitch; no quarter-tone precision.
- **Segment speed artefact:** `speed_centre = Δcentre/Δt` diverges when picks are very close in time; **net_speed** and **straightness** remain stable. See `sampling_warnings` in export.
- **GUI-only workflow** for picking; computation is pure Python (`compute_vd10`) and exportable to JSON.
