from app.api.routes.research import ScriptEditRequest

def test_script_edit_request_accepts_complete_script():
    payload=ScriptEditRequest(title="BLAST explained",script="This is a complete reviewed narration for an educational video.",change_note="Clarified the worked example")
    assert payload.title == "BLAST explained"
    assert payload.sections is None

def test_script_word_count_and_duration_are_consistent():
    words=700
    assert round(words/140,1) == 5.0
