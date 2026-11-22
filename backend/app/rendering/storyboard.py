"""Generate a timed visual storyboard from the approved narration."""
from typing import Any
from app.agents.pipeline import _call_model

def build_storyboard(script: str, title: str, max_scenes: int = 20) -> list[dict[str, Any]]:
    result = _call_model(
        "video_storyboard", "BioinfoBeats Visual Storyboard Director",
        "Turn the supplied narration into a concise sequence of visual scenes. Return JSON with scenes array. Each scene must contain narration_excerpt (verbatim short excerpt from script), prompt (visual description only, no text), and transition (one of cut, fade). Use 4 to 20 scenes, cover the complete narration in order, avoid repeating visuals, use scientifically accurate educational imagery and visual metaphors. No on-screen words or labels in generated images. Do not invent scientific claims.",
        {"title": title, "script": script, "brand_style": "premium cinematic science education, deep navy and electric cyan"}
    )
    scenes = result.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("Storyboard agent did not return a scenes list.")
    output = []
    for item in scenes[:max_scenes]:
        prompt = str(item.get("prompt", "")).strip()
        excerpt = str(item.get("narration_excerpt", "")).strip()
        if len(prompt) < 8:
            continue
        output.append({"prompt": prompt[:700], "narration_excerpt": excerpt[:1200], "transition": item.get("transition", "fade") if item.get("transition") in {"cut", "fade"} else "fade"})
    if len(output) < 2:
        raise ValueError("Storyboard must contain at least two usable visual scenes.")
    return output
