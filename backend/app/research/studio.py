"""Source-grounded research-to-script generation."""
from typing import Any
from app.agents.pipeline import _call_model
from app.research.providers import web_search, youtube_search, ResearchConfigurationError

def create_research_script(topic: str, audience: str, duration_minutes: int, include_youtube: bool = True) -> dict[str, Any]:
    web = web_search(topic, max_results=8)
    sources = []
    for index, item in enumerate(web.get("results", []), 1):
        sources.append({"source_id": f"W{index}", "type": "web", **item})
    youtube = {"results": []}
    if include_youtube:
        try:
            youtube = youtube_search(topic, max_results=5)
        except ResearchConfigurationError:
            youtube = {"results": []}
        for index, item in enumerate(youtube.get("results", []), 1):
            sources.append({"source_id": f"Y{index}", "type": "youtube", **item})
    if not any(source.get("url") for source in sources):
        raise ValueError("No source results were retrieved. Refine the topic or check your research provider.")
    target_words = duration_minutes * 135
    draft = _call_model(
        "research_script_writer", "BioinfoBeats Research Editor",
        "Create an educational YouTube script grounded strictly in the supplied source records and well-established background knowledge. Target the requested duration at approximately 130-145 spoken words per minute. Return JSON with title, hook, learning_objectives (array), sections (array of objects with heading, narration, visual_direction, example), full_script, key_claims (array of objects with claim, source_ids array, confidence high/medium/low), and references (array of source_ids). For every externally verifiable factual claim, attach only source_ids that directly support it. Never invent a source, URL, quote, statistic, study result, or DOI. If sources do not support a claim, mark it as needing verification. Include at least one practical worked example. End with a concise recap. Do not include citations as fabricated author-year text.",
        {"topic": topic, "audience": audience, "duration_minutes": duration_minutes, "approximate_target_words": target_words, "source_records": sources}
    )
    claims = draft.get("key_claims", [])
    valid_ids = {item["source_id"] for item in sources}
    for claim in claims if isinstance(claims, list) else []:
        claim["source_ids"] = [sid for sid in claim.get("source_ids", []) if sid in valid_ids]
        if not claim["source_ids"]:
            claim["confidence"] = "needs_verification"
    verification = _call_model(
        "research_fact_audit", "BioinfoBeats Scientific Fact Auditor",
        "Audit the supplied script and claim list against the exact supplied source records. Do not browse or use outside assumptions. Return JSON with overall_status (supported/needs_review), verified_claims (array), unsupported_claims (array), corrections (array), missing_context (array), and editorial_notes (array). A claim is supported only when one or more supplied source records actually substantiate it. If evidence is ambiguous or snippets are insufficient, mark it needs_review. Do not invent citations.",
        {"topic": topic, "full_script": draft.get("full_script", ""), "key_claims": claims, "source_records": sources}
    )
    return {
        "title": str(draft.get("title") or topic)[:300],
        "hook": draft.get("hook", ""),
        "learning_objectives": draft.get("learning_objectives", []),
        "sections": draft.get("sections", []),
        "script": str(draft.get("full_script") or ""),
        "claims": claims,
        "references": draft.get("references", []),
        "sources": sources,
        "fact_check": verification,
        "word_count": len(str(draft.get("full_script") or "").split()),
        "target_duration_minutes": duration_minutes,
    }
