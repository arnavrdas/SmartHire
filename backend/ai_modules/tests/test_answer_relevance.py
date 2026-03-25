from ai_modules.answer_relevance import evaluate_answer_relevance

def test_relevance_empty():
    result = evaluate_answer_relevance("", "")
    assert result["relevance_score"] == 0.0

def test_relevance_valid():
    candidate = "I know Python and FastAPI."
    expected = "Candidate should know Python and FastAPI."
    result = evaluate_answer_relevance(candidate, expected)
    assert 0.0 <= result["relevance_score"] <= 1.0