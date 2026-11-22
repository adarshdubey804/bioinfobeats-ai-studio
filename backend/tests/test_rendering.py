from pathlib import Path
from app.rendering.service import build_srt, _scene_durations

def test_srt_captions_fill_audio_duration(tmp_path):
    output = tmp_path / "captions.srt"
    build_srt("First sentence. Second sentence!", output, duration_seconds=10)
    text = output.read_text()
    assert "00:00:10,000" in text
    assert "First sentence." in text
    assert "Second sentence!" in text

def test_scene_durations_sum_to_narration_duration():
    scenes = [{"narration_excerpt":"one two three"},{"narration_excerpt":"four five"}]
    values = _scene_durations(scenes, "one two three four five", 25.0)
    assert len(values) == 2
    assert round(sum(values), 5) == 25.0



def test_scene_duration_rejects_out_of_range_values():
    import pytest
    with pytest.raises(ValueError, match="between 1 and 180"):
        _scene_durations([{"duration_seconds": 181}], "sample", 10)


def test_render_output_rejects_missing_file(tmp_path):
    import pytest
    from app.rendering.service import _validate_render_output, RenderCommandError
    with pytest.raises(RenderCommandError, match="missing or unexpectedly small"):
        _validate_render_output(tmp_path / "missing.mp4")


def test_progress_callback_receives_stage_updates():
    from app.rendering.service import _report_progress
    events = []
    _report_progress(events.append, "audio_mix", 90, "Mixing audio")
    assert events == [{"stage": "audio_mix", "percent": 90, "message": "Mixing audio"}]



def test_pronunciation_dictionary_replaces_whole_terms_case_insensitively():
    from app.rendering.service import apply_pronunciation_dictionary
    spoken = apply_pronunciation_dictionary("BLAST aligns FASTA sequences; blast is fast.", "BLAST=blast\nFASTA=fast-a")
    assert spoken == "blast aligns fast-a sequences; blast is fast."


def test_pronunciation_dictionary_does_not_replace_inside_other_words():
    from app.rendering.service import apply_pronunciation_dictionary
    assert apply_pronunciation_dictionary("blast blastn", "blast=blɑːst") == "blɑːst blastn"


def test_pronunciation_dictionary_rejects_malformed_entries():
    import pytest
    from app.rendering.service import apply_pronunciation_dictionary
    with pytest.raises(ValueError, match="TERM=PRONUNCIATION"):
        apply_pronunciation_dictionary("BLAST", "BLAST")
