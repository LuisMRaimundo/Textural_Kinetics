from granular_v2.loader import load_score_and_note_matrix


def test_single_parse(sample_musicxml):
    score, nm, audit = load_score_and_note_matrix(sample_musicxml, merge_ties=True)
    assert score is not None
    assert len(nm) > 0
    assert "onset_sec" in nm[0]
    assert nm[0]["onset_sec"] >= 0
    assert "source" in audit
