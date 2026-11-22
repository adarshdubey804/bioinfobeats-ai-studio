from app.agents.base import AgentSpec
AGENTS = [
    AgentSpec('topic_researcher', 'Topic Researcher', 'Find relevant topics, trends and primary sources.', ('brand', 'audience'), ('topics', 'sources')),
    AgentSpec('fact_checker', 'Fact-check Researcher', 'Verify claims and preserve citations and uncertainty.', ('draft_claims', 'sources'), ('verified_claims', 'caveats')),
    AgentSpec('competitor_researcher', 'Competitor Researcher', 'Analyze public competitor content and identify content gaps.', ('competitors', 'platforms'), ('patterns', 'content_gaps')),
    AgentSpec('video_generator', 'AI Video Generator', 'Prepare scripts and provider-neutral avatar/video generation jobs.', ('script', 'format'), ('generation_request',)),
    AgentSpec('video_editor', 'Video Editor', 'Create deterministic edit plans and FFmpeg task specifications.', ('raw_media', 'edit_brief'), ('edit_plan', 'captions')),
    AgentSpec('creative_publisher', 'Creative & Publishing Agent', 'Prepare poster briefs and channel-specific publishing packages for approval.', ('approved_media', 'channels'), ('creative_brief', 'publishing_package')),
]
