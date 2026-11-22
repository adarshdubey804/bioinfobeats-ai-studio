from app.agents.pipeline import AGENT_PROMPTS, run_pipeline, AgentConfigurationError
from app.core.config import settings

def test_pipeline_registers_six_sequential_agents():
    assert len(AGENT_PROMPTS) == 6
    assert [item[0] for item in AGENT_PROMPTS] == [
        'topic_researcher', 'fact_checker', 'competitor_researcher',
        'video_generator', 'video_editor', 'creative_publisher'
    ]

def test_pipeline_requires_provider_key(monkeypatch):
    monkeypatch.setattr(settings, 'llm_api_key', '')
    try:
        run_pipeline('BLAST explained', {})
        assert False, 'Expected missing provider key to stop execution'
    except AgentConfigurationError as exc:
        assert 'LLM_API_KEY' in str(exc)
