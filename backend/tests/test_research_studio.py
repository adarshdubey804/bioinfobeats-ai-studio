from app.research.studio import create_research_script

def test_research_studio_filters_unknown_source_ids(monkeypatch):
    import app.research.studio as studio
    calls = {"count": 0}
    def fake_call(agent_key, agent_name, instruction, context):
        calls["count"] += 1
        if calls["count"] == 1:
            return {"title":"Test","full_script":"A scientifically careful explanation.","sections":[{"heading":"Intro","narration":"Hello","visual_direction":"Molecule","example":"Example"}],"key_claims":[{"claim":"Claim A","source_ids":["W1","FAKE"],"confidence":"high"},{"claim":"Claim B","source_ids":["FAKE"],"confidence":"high"}],"references":["W1"]}
        return {"overall_status":"needs_review","verified_claims":[],"unsupported_claims":["Claim B"],"corrections":[],"missing_context":[],"editorial_notes":[]}
    monkeypatch.setattr(studio, "web_search", lambda topic,max_results: {"results":[{"title":"Paper","url":"https://example.org/paper","snippet":"A supported fact."}]})
    monkeypatch.setattr(studio, "youtube_search", lambda topic,max_results: {"results":[]})
    monkeypatch.setattr(studio, "_call_model", fake_call)
    result=create_research_script("Test topic","Learners",5,True)
    assert result["claims"][0]["source_ids"] == ["W1"]
    assert result["claims"][1]["source_ids"] == []
    assert result["claims"][1]["confidence"] == "needs_verification"
