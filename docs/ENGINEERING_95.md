# Engineering path to 95+ (Granular_v2)

What is **implemented in software** vs what remains **thesis / corpus work**.

## Done in v1.0.5 (engineering)

1. **Offset class closed in Granular_v2** — central `offsets.py`, Mustextu legacy path aligned, static + corpus tests.
2. **Structured degradation** — `tempo_audit.warnings[]` with `{code, message}`; `tempo_model: stepwise_plateau`.
3. **Corpus regression** — three MusicXML fixtures + `compare_all.py`.
4. **CI** — Ubuntu + Windows, Python 3.10–3.11, pytest + corpus + mypy (core modules).

## Still required for defensible 95 (not all automatable here)

| Item | Owner | Notes |
|------|-------|-------|
| Real repertoire corpus | Thesis | Add MusicXML from editors (Sibelius, Dorico, MuseScore); manual spot-check rates |
| Sibling tools audit | Port | Granularidade + horizontal_v3 still have raw `.offset` (see OFFSET_AUDIT.md) |
| Accelerandi / continuous tempo | Document + warn | Stepwise plateau only; claim limits in thesis |
| Doctoral argument | Writing | Mustextu theory + multidimensional apparatus — not a commit |

## Score rubric (engineering only)

| Version | Engineering /100 |
|---------|------------------|
| v1.0.3 (util_tempo only) | ~72 |
| v1.0.4 (timebase + notes) | ~88–90 |
| v1.0.5 (audit + warnings + tests + CI) | ~92–94 |
| + real corpus + sibling port | ~95 |
