from app.agents.registry import AGENTS
def test_six_agents_registered():
 assert len(AGENTS)==6
 assert len({a.key for a in AGENTS})==6
