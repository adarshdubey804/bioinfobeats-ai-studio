from app.research.providers import web_search, youtube_search, ResearchConfigurationError
from app.core.config import settings

def test_web_search_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, 'tavily_api_key', '')
    try:
        web_search('bioinformatics trends')
        assert False, 'Expected configuration error'
    except ResearchConfigurationError as exc:
        assert 'TAVILY_API_KEY' in str(exc)

def test_youtube_search_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, 'youtube_api_key', '')
    try:
        youtube_search('BLAST tutorial')
        assert False, 'Expected configuration error'
    except ResearchConfigurationError as exc:
        assert 'YOUTUBE_API_KEY' in str(exc)
