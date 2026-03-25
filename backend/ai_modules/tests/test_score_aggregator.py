from ai_modules.score_aggregator import aggregate_scores

def test_aggregate_scores_valid():
    whisper_out = {"transcript": "Hello", "confidence": 0.9}
    speech_out = {"confidence_score": 0.8}
    emotion_out = {"happy": 0.5, "neutral": 0.4}
    relevance_out = {"relevance_score": 0.85}

    result = aggregate_scores(whisper_out, speech_out, emotion_out, relevance_out)
    assert "final_score" in result
    assert 0.0 <= result["final_score"] <= 1.0