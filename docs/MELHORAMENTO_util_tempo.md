# Granular_v2 — instruções de melhoramento (util_tempo)

## Prioridade 1 — Corrigido em v1.0.3

`build_seconds_map` usava `getattr(elem, "offset", default)` em tuplos `(float, float, MetronomeMark)`.
Cada segmento abrangia a peça inteira → `fn(4.0)` devolvia 6.0 s em vez de 3.0 s (120→60 BPM).

**Correção:** `_boundary_offset()` + `tempo_info` no callable.

**Export:** `tempo_audit` em `analysis.json` via `loader` → `run_full_analysis`.

## Prioridade 2 — Documentado

Andamento em degraus entre `MetronomeMark`; ver `docs/LIMITATIONS.md` e docstring do módulo.

## v1.0.4 — offset global (measure-local bug)

Mesmo erro de raiz em `timebase.build_tempo_segments` (`mm.offset`) e
`note_extraction` (`el.offset`). Corrigido com `getOffsetInHierarchy`.
Referência `sparse_homophony.json` regenerada (0.75 ev/s fused EPS global pós-VD4 v1.0.7; 2.25 ev/s = taxa raw note-matrix / span).

## Prioridade 3 — Cobertura

`tests/test_util_tempo_branches.py` + `tests/test_global_offsets_integration.py`.
