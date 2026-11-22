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
