# Event-rate formulas (Granular_v2)

## Global

- \(N\) = number of onset events (after optional tie merge)
- \(T_{\mathrm{span}} = t_N - t_1\) (seconds between first and last onset)
- **events_per_second** = \(N / T_{\mathrm{span}}\)
- **events_per_millisecond** = events_per_second / 1000

## Per time bin (width \(\Delta\) seconds)

- **onset_count_per_bin** = attacks in \([t, t+\Delta)\)
- **events_per_second_per_bin** = onset_count / \(\Delta\)

## Per millisecond window (width \(W\) ms)

- **events_per_millisecond_in_window** = count in window / \(W\)

## Per bar (measure \(m\))

- **onset_count** = attacks with onset in measure \(m\)
- **events_per_second_in_bar** = onset_count / measure_duration_sec
- **events_per_beat_in_bar** = onset_count / notated_beats_in_bar

## Mustextu

- **rate_events_per_second** (`rate_eps`) = unique merged onsets / (window_ms / 1000)
