import granular_v2.loader as loader_mod
from granular_v2.loader import load_score_and_note_matrix


def _warning_codes(audit) -> list[str]:
    return [w["code"] for w in audit.get("warnings", [])]


def test_single_parse(sample_musicxml):
    score, nm, audit = load_score_and_note_matrix(sample_musicxml, merge_ties=True)
    assert score is not None
    assert len(nm) > 0
    assert "onset_sec" in nm[0]
    assert nm[0]["onset_sec"] >= 0
    assert "source" in audit


def test_temporal_fallback_to_metronome_boundaries(sample_musicxml, monkeypatch):
    real_bts = loader_mod.build_tempo_segments
    calls = {"n": 0}

    def _raise_first(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("simulated build_tempo_segments failure")
        return real_bts(*args, **kwargs)

    monkeypatch.setattr(loader_mod, "build_tempo_segments", _raise_first)

    score, nm, audit = load_score_and_note_matrix(sample_musicxml, merge_ties=True)

    assert score is not None
    assert len(nm) > 0
    assert all(n["onset_sec"] >= 0 for n in nm)
    assert "timebase_segments_failed" in _warning_codes(audit)
    assert audit.get("source") == "metronomeMarkBoundaries"


def test_double_temporal_fallback_uniform_segment(sample_musicxml, monkeypatch):
    real_bts = loader_mod.build_tempo_segments
    calls = {"n": 0}

    def _raise_first(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("simulated build_tempo_segments failure")
        return real_bts(*args, **kwargs)

    def _raise_seconds_map(*args, **kwargs):
        raise RuntimeError("simulated build_seconds_map failure")

    monkeypatch.setattr(loader_mod, "build_tempo_segments", _raise_first)
    monkeypatch.setattr(loader_mod, "build_seconds_map", _raise_seconds_map)

    score, nm, audit = load_score_and_note_matrix(
        sample_musicxml, merge_ties=True, default_bpm=120.0
    )

    assert score is not None
    assert len(nm) > 0
    assert all(n["duration_sec"] > 0 for n in nm)
    codes = _warning_codes(audit)
    assert "timebase_segments_failed" in codes
    assert "metronome_boundaries_failed" in codes
    assert audit.get("source") == "timebase_segments"
    assert audit.get("reason") == "uniform segment map"
    assert audit.get("tempo_fallback_used") is True


def test_midi_branch(tmp_path, sample_musicxml):
    from music21 import converter

    score = converter.parse(str(sample_musicxml))
    midi_path = tmp_path / "sample.mid"
    score.write("midi", fp=str(midi_path))

    score, nm, audit = load_score_and_note_matrix(midi_path)

    assert score is not None
    assert len(nm) > 0
    assert "onset_sec" in nm[0]
    assert nm[0]["onset_sec"] >= 0
    assert audit["source"] == "midi_seconds"
    assert audit.get("warnings") == []


def test_sounding_pitch_transposing_instrument(tmp_path):
    from music21 import instrument, note, stream

    path = tmp_path / "clarinet.musicxml"
    part = stream.Part()
    part.insert(0, instrument.Clarinet())
    measure = stream.Measure()
    measure.append(note.Note("C4", quarterLength=1))
    part.append(measure)
    score_obj = stream.Score()
    score_obj.insert(0, part)
    score_obj.write("musicxml", fp=str(path))

    _, nm_written, audit_written = load_score_and_note_matrix(
        path, pitch_domain="written", merge_ties=True
    )
    _, nm_sounding, audit_sounding = load_score_and_note_matrix(
        path, pitch_domain="sounding", merge_ties=True
    )

    assert len(nm_written) == 1
    assert len(nm_sounding) == 1
    written_pitch = nm_written[0]["pitch"]
    sounding_pitch = nm_sounding[0]["pitch"]
    assert written_pitch != sounding_pitch
    assert written_pitch == 60
    assert sounding_pitch == 58

    for nm, audit in ((nm_written, audit_written), (nm_sounding, audit_sounding)):
        row = nm[0]
        assert row["onset_sec"] >= 0
        assert row["duration_sec"] > 0
        assert isinstance(row["pitch"], int)
        assert "sounding_pitch_failed" not in _warning_codes(audit)
