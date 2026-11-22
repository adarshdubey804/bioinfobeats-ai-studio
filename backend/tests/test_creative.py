from app.creative.service import create_creative_package
from app.core.config import settings
import pytest

def test_creative_package_requires_exactly_three_concepts(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "media_storage_dir", str(tmp_path))
    def fake_call(*args, **kwargs):
        return {"thumbnail_concepts": [{"name": "one", "image_prompt": "DNA"}]}
    monkeypatch.setattr("app.creative.service._call_model", fake_call)
    with pytest.raises(ValueError, match="exactly three"):
        create_creative_package("workflow-1234", "BLAST", "BLAST in 5 minutes", "Long script", ["YouTube"])
