"""Creative metadata and thumbnail generation for workflow assets."""
from pathlib import Path
from typing import Any
from app.agents.pipeline import _call_model
from app.rendering.visuals import generate_scene_image
from app.core.config import settings

def create_creative_package(workflow_id: str, topic: str, title: str, script: str, platforms: list[str]) -> dict[str, Any]:
    brief = _call_model(
        "creative_package", "BioinfoBeats Creative Director",
        "Create platform-ready metadata and exactly three distinct thumbnail concepts. Return JSON with youtube_title (max 70 chars), youtube_description, hashtags (array), instagram_caption, linkedin_caption, thumbnail_concepts (array of exactly 3 objects, each with name and image_prompt). Prompts must describe compelling, scientifically accurate, high-contrast editorial imagery with a clear focal subject, deep navy and electric cyan brand palette, no text, no logos, no watermark. Do not invent facts or claim outcomes unsupported by the script.",
        {"topic": topic, "working_title": title, "script": script, "platforms": platforms, "brand": "BioinfoBeats"},
    )
    concepts = brief.get("thumbnail_concepts", [])
    if len(concepts) != 3:
        raise ValueError("Creative agent must return exactly three thumbnail concepts.")
    output_dir = Path(settings.media_storage_dir).resolve() / workflow_id / "creative"
    output_dir.mkdir(parents=True, exist_ok=True)
    thumbnails = []
    for index, concept in enumerate(concepts, 1):
        prompt = (
            "Create a premium YouTube thumbnail background image, 16:9 landscape composition, "
            "designed for strong readability when viewed small. Keep the left or right third uncluttered "
            "for later text overlay. Do not render any text, letters, numbers, logos or watermarks. "
            "Use cinematic lighting, crisp scientific detail, deep navy and electric cyan BioinfoBeats style. "
            + str(concept.get("image_prompt", "Scientific bioinformatics visual about " + topic))
        )
        path = output_dir / f"thumbnail-{index}.png"
        generate_scene_image(prompt, path, "landscape")
        thumbnails.append({
            "name": str(concept.get("name", f"Concept {index}")),
            "url": f"/media/{workflow_id}/creative/thumbnail-{index}.png",
        })
    return {**brief, "thumbnails": thumbnails, "status": "ready_for_review"}
