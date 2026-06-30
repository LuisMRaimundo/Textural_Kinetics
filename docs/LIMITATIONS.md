# Textural_Kinetics — documented limitations

## Tempo → seconds (stepwise model)

`build_seconds_map` and `timebase.build_tempo_segments` treat tempo as **piecewise constant** between successive `MetronomeMark` entries. Accelerandi, ritardandi, and other continuous tempo curves are approximated as plateaus. Event rates in seconds are therefore tied to notated metronome marks, not to performance timing.

## Symbolic analysis only

Heatmaps and “spectral” grids are **notation-based** (pitch × time, velocity-weighted). They do not represent measured audio spectra or psychoacoustic loudness.

Scalar metrics (EPS global, IOI CV, synchrony fraction, burstiness) are likewise **score-derived model outputs**, not perceptual measures. VD4 IOI CV / granularity index / burstiness use **fused onsets** (τ = 2 ms); raw diagnostics and Mustextu rates are documented separately. See **[METRIC_SEMANTICS.md](METRIC_SEMANTICS.md)**.

## Mustextu coincidence merge

Onsets within `coincidence_ms` of a group **anchor** are merged. This avoids transitive chaining across distant onsets (fixed in v1.0.1).

## Partitional layer

Optional partition indices are simplified (channel-based); not a complete partitional formalism. Only `partition_mode="channels"` implements agglomeration/dispersion; `"rhythmic"` and `"linear"` are config stubs (active-count fallback only).

## VD10 registral trajectory

- **User-defined block (default):** manual picks on the heatmap. Optional **Auto-pick from score** fills one block per XML part from the loaded note matrix (editable afterward). Optional **Group selected parts** merges several parts into one envelope block (appends; editable afterward).
- **Note-map display:** part-coloured registral lines on the VD10 heatmap are visual only; they do not change metrics.
- **Separate from granularity:** high event rate does not imply registral motion; a registral round-trip can yield **net_speed ≈ 0** while `total_path` is large.
- **Semitone resolution:** picks snap to integer MIDI pitch; no quarter-tone precision.
- **Segment speed artefact:** `speed_centre = Δcentre/Δt` diverges when picks are very close in time; **net_speed** and **straightness** remain stable. See `sampling_warnings` in export.
- **Multi-block:** each block is independent; relations describe inter-block geometry only, not merged VD10.
- **Heatmap picking:** interactive edit on the embedded advanced heatmap (MusicXML/MIDI loaded on Analysis tab).
- **Image picking (v1.0.12):** PNG/JPG excerpt with two-axis linear calibration; assumes **proportional graphic / spatial layout** — not valid for conventional non-spatial symbolic notation where image position does not encode pitch or duration.
- **Calibration error:** equal pixel reference points on an axis are rejected (`TrajectoryCalibrationError`).
- **Computation:** pure Python (`compute_vd10`, `compute_vd10_session`, `make_axis_calibration`); GUI is for interactive sampling only.
