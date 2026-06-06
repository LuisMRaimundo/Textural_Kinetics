# Metric reference (Granularity Analyser)

Compact definitions. Full derivations and algorithms: **[MANUAL_TECNICO.md](MANUAL_TECNICO.md)**.  
**Interpretive limits** (what each metric does *not* mean): **[METRIC_SEMANTICS.md](METRIC_SEMANTICS.md)**.

## Event rates (global)

| Metric | Unit | Formula |
|--------|------|---------|
| `events_per_second` | s⁻¹ | \(N / T_{\mathrm{span}}\) |
| `events_per_millisecond` | ms⁻¹ | `events_per_second` / 1000 |

\(N\) = note-matrix rows (one onset per event, not deduplicated); \(T_{\mathrm{span}} = t_{\mathrm{last\,onset}} - t_{\mathrm{first\,onset}}\) (seconds; 1 s if degenerate). Not full score duration — see [METRIC_SEMANTICS.md](METRIC_SEMANTICS.md) §3.

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
| IOI\(_k\) | \(t_{k+1} - t_k\) on **sorted raw event onsets** (zero IOIs if simultaneous) |
| `ioi_cv` | \(\sigma_{\mathrm{IOI}} / \mu_{\mathrm{IOI}}\) on those IOIs |
| `granularity_index` | \(1 / (1 + \mathrm{ioi\_cv})\) |
| `burstiness` | \((\sigma - \mu) / (\sigma + \mu)\) on **0.5 s** binned onset counts |

## Mustextu (composite)

| Metric | Formula |
|--------|---------|
| `rate_eps` | \(N_{\mathrm{unique}} / T_{\mathrm{win}}\) (events/s) |
| `rate_eps_raw` | \(N_{\mathrm{raw}} / T_{\mathrm{win}}\) |
| `synchrony_fraction` (`sync_fraction`) | \(1 - N_{\mathrm{unique}}/N_{\mathrm{raw}}\) after τ-merge of **all layer** onsets (ms); not vertical pitch count |
| `granularity_score` | \(\mathrm{clip}( \mathrm{rate\_eps} / \mathrm{gran\_max\_eps},\, 0,\, 1)\) |
| GCD/LCM (regular layers) | analytic coincidence on integer events/beat |

## Heatmaps (symbolic)

| View | Quantity |
|------|----------|
| Basic | \(\log(1 + H_{p,t})\) occupancy |
| Advanced | smoothed, gamma, percentile-scaled \(H\) |
| Spectral | velocity-weighted energy grid \(E_{p,t}\) |

Not measured audio spectra.
