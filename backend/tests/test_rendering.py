from pathlib import Path
import pytest
from app.rendering.service import build_srt, _safe_id

def test_build_srt_creates_sentence_captions(tmp_path: Path):
    target = tmp_path / "captions.srt"
    build_srt("BLAST finds similar sequences. It helps compare DNA!", target)
    content = target.read_text()
    assert "1\\n00:00:00,000 -->" in content
    assert "BLAST finds similar sequences." in content
    assert "2\\n" in content

def test_render_id_rejects_path_traversal():
    with pytest.raises(ValueError):
        _safe_id("../../etc/passwd")
