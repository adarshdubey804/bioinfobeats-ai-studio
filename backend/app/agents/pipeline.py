"""Sequential six-agent content pipeline using an OpenAI-compatible chat API."""
import json
from typing import Any
import httpx
from app.core.config import settings

AGENT_PROMPTS = [
    ("topic_researcher", "Topic Researcher", "Create a research brief and 5 strong content angles for the given brand, audience and topic. Do not invent live trends or sources. Return source_queries for claims that need external research."),
    ("fact_checker", "Fact-check Researcher", "Review the research brief and claims. Separate well-supported general knowledge from claims requiring verification. Never invent citations. Return claims_to_verify, risks, and safe_claims."),
    ("competitor_researcher", "Competitor Researcher", "Analyze competitor names and platform context supplied by the user. If no verified competitor evidence is included, do not pretend to have browsed. Return competitor_research_queries, likely positioning hypotheses clearly labelled as hypotheses, and content_gaps."),
    ("video_generator", "AI Video Generator", "Turn the selected content angle into a production-ready short-form video script and avatar-generation brief. Include hook, scenes, narration, visual prompts, on-screen text, and target duration. Do not claim a video file was rendered."),
    ("video_editor", "Video Editor", "Create a practical editing specification from the script: scene timeline, transitions, B-roll, captions, sound design, aspect ratios and export settings. Return an edit decision list; do not claim to have edited a file."),
    ("creative_publisher", "Creative & Publishing Agent", "Create a poster/thumbnail creative brief and platform-specific draft copy, hashtags and publishing checklist. Mark every item as a draft requiring human approval. Never publish or schedule anything."),
]

class AgentConfigurationError(RuntimeError):
    pass

def _call_model(agent_key: str, agent_name: str, instruction: str, context: dict[str, Any]) -> dict[str, Any]:
    if not settings.llm_api_key:
        raise AgentConfigurationError("LLM_API_KEY is missing. Configure an AI provider key before queueing workflows.")
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.llm_model,
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "You are a specialist in a professional social-media production studio. Return valid JSON only. Be transparent about uncertainty. Never fabricate sources, competitor observations, analytics, or completed external actions."},
            {"role": "user", "content": json.dumps({"agent": agent_name, "task": instruction, "workflow_context": context}, ensure_ascii=False, default=str)},
        ],
    }
    try:
        response = httpx.post(url, json=payload, headers={"Authorization": f"Bearer {settings.llm_api_key}"}, timeout=settings.llm_timeout_seconds)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        result = json.loads(content)
        if not isinstance(result, dict):
            raise ValueError("Agent response must be a JSON object")
        return result
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{agent_key} failed: {exc}") from exc

def run_pipeline(topic: str, workflow_config: dict[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {
        "topic": topic,
        "brand": workflow_config.get("brand", "BioinfoBeats"),
        "audience": workflow_config.get("audience", "Bioinformatics learners and life-science researchers"),
        "platforms": workflow_config.get("platforms", ["YouTube", "Instagram", "LinkedIn"]),
        "competitors": workflow_config.get("competitors", []),
        "format": workflow_config.get("format", "short-form video"),
        "target_duration_seconds": workflow_config.get("target_duration_seconds", 60),
        "user_brief": workflow_config.get("brief", ""),
    }
    outputs: dict[str, Any] = {}
    for key, name, instruction in AGENT_PROMPTS:
        result = _call_model(key, name, instruction, {**context, "previous_agent_outputs": outputs})
        outputs[key] = result
    return outputs
