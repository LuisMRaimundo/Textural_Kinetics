# Granular_v2 — documented limitations

## Tempo → seconds (stepwise model)

`build_seconds_map` and `timebase.build_tempo_segments` treat tempo as **piecewise constant** between successive `MetronomeMark` entries. Accelerandi, ritardandi, and other continuous tempo curves are approximated as plateaus. Event rates in seconds are therefore tied to notated metronome marks, not to performance timing.

## Symbolic analysis only

Heatmaps and “spectral” grids are **notation-based** (pitch × time, velocity-weighted). They do not represent measured audio spectra or psychoacoustic loudness.

## Mustextu coincidence merge

Onsets within `coincidence_ms` of a group **anchor** are merged. This avoids transitive chaining across distant onsets (fixed in v1.0.1).

## Partitional layer

Optional partition indices are simplified (channel-based); not full Gentil-Nunes / PARSEMAT equivalence.
