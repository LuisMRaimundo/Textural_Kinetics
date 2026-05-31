# Corpus de referência (regressão)

## Localização

- **Fixtures:** `corpus/fixtures/*.musicxml`
- **Referências:** `corpus/reference/*.json`
- **Script:** `corpus/scripts/compare_all.py`

## Fixtures

| Ficheiro | Descrição | Métricas guardadas |
|----------|-----------|-------------------|
| `sparse_homophony.musicxml` | 2 compassos, 60 BPM, acordes homofónicos | `num_events`, `events_per_second`, `rate_eps` (Mustextu) |
| `layered_async.musicxml` | Camadas com desfasamento | idem |
| `dense_onset_burst.musicxml` | Rajada de onsets | idem |

As referências foram geradas com **offsets globais** (v1.0.4+). Valores antigos que assumiam offsets measure-local estão obsoletos (ex.: `sparse_homophony` passou de 4.5 para **2.25** ev/s).

## Executar comparação

```bash
python corpus/scripts/compare_all.py
```

Tolerâncias: `events_per_second` ±1e-5; Mustextu `rate_eps` ±0.02.

## Regenerar referências

Após alteração intencional de métricas:

```bash
Remove-Item corpus/reference/*.json   # PowerShell
python corpus/scripts/compare_all.py  # escreve JSON em falta
```

Rever diffs antes de commitar referências novas.

## Testes automáticos

- `tests/test_corpus.py` — integração pipeline
- `tests/test_offset_audit.py` — invariantes de span temporal por fixture

Ver **[MANUAL_TECNICO.md](MANUAL_TECNICO.md)** § Tutorial e § Validação.
