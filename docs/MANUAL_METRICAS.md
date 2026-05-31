# Metric reference (Granularity Analyser)

Compact definitions. Full derivations and algorithms: **[MANUAL_TECNICO.md](MANUAL_TECNICO.md)**.

## Event rates (global)

| Metric | Unit | Formula |
|--------|------|---------|
| `events_per_second` | s⁻¹ | \(N / T_{\mathrm{span}}\) |
| `events_per_millisecond` | ms⁻¹ | `events_per_second` / 1000 |

\(N\) = note onsets; \(T_{\mathrm{span}} = t_{\max} - t_{\min}\) (seconds).

## Per time bin (width \(\Delta\) s)

| Metric | Formula |
|--------|---------|
| `onset_count_per_bin` | attacks in \([t, t+\Delta)\) |
| `events_per_second_per_bin` | count / \(\Delta\) |

## Per millisecond window (width \(W\) ms)

| Metric | Formula |
|--------|---------|
| `events_per_millisecond_in_window` | count in \([t, t+W]\) / \(W\) |

## Per bar

| Metric | Formula |
|--------|---------|
| `events_per_second_in_bar` | onsets in bar / bar duration (s) |
| `events_per_beat_in_bar` | onsets in bar / notated beats |

## Activity / IOI

| Metric | Formula |
|--------|---------|
| IOI\(_k\) | \(t_{k+1} - t_k\) |
| `ioi_cv` | \(\sigma_{\mathrm{IOI}} / \mu_{\mathrm{IOI}}\) |
| `granularity_index` | \(1 / (1 + \mathrm{ioi\_cv})\) |
| `burstiness` | \((\sigma - \mu) / (\sigma + \mu)\) on binned onset counts |

## Mustextu (composite)

| Metric | Formula |
|--------|---------|
| `rate_eps` | \(N_{\mathrm{unique}} / T_{\mathrm{win}}\) (events/s) |
| `rate_eps_raw` | \(N_{\mathrm{raw}} / T_{\mathrm{win}}\) |
| `synchrony_fraction` | \(1 - N_{\mathrm{unique}}/N_{\mathrm{raw}}\) |
| `granularity_score` | \(\mathrm{clip}( \mathrm{rate\_eps} / \mathrm{gran\_max\_eps},\, 0,\, 1)\) |
| GCD/LCM (regular layers) | analytic coincidence on integer events/beat |

## Heatmaps (symbolic)

| View | Quantity |
|------|----------|
| Basic | \(\log(1 + H_{p,t})\) occupancy |
| Advanced | smoothed, gamma, percentile-scaled \(H\) |
| Spectral | velocity-weighted energy grid \(E_{p,t}\) |

Not measured audio spectra.
