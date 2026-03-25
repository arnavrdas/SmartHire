from typing import Dict

def aggregate_scores(
    whisper_output: Dict,
    speech_output: Dict,
    emotion_output: Dict,
    relevance_output: Dict,
    weights: Dict = None
) -> dict:
    """
    Aggregate scores from all AI modules into a final candidate score.
    
    Args:
        whisper_output (dict): Transcript + confidence from Whisper
        speech_output (dict): Clarity, pause ratio, confidence from Librosa
        emotion_output (dict): Emotion distribution from DeepFace
        relevance_output (dict): Answer relevance from Sentence-Transformers
        weights (dict): Custom weights for each module
    
    Returns:
        dict: Final aggregated score and breakdown
    """
    # Default weights (can be tuned later by HR team)
    if weights is None:
        weights = {
            "whisper_confidence": 0.25,
            "speech_confidence": 0.20,
            "emotion_stability": 0.25,
            "answer_relevance": 0.30
        }

    # Extract values safely
    whisper_conf = whisper_output.get("confidence", 0.0)
    speech_conf = speech_output.get("confidence_score", 0.0)
    relevance = relevance_output.get("relevance_score", 0.0)

    # Emotion stability = proportion of "neutral" + "happy"
    emotion_scores = emotion_output or {}
    emotion_stability = emotion_scores.get("neutral", 0.0) + emotion_scores.get("happy", 0.0)

    # Weighted sum
    final_score = (
        whisper_conf * weights["whisper_confidence"] +
        speech_conf * weights["speech_confidence"] +
        emotion_stability * weights["emotion_stability"] +
        relevance * weights["answer_relevance"]
    )

    return {
        "final_score": round(final_score, 3),
        "breakdown": {
            "whisper_confidence": whisper_conf,
            "speech_confidence": speech_conf,
            "emotion_stability": round(emotion_stability, 3),
            "answer_relevance": relevance
        },
        "weights": weights
    }

if __name__ == "__main__":
    # Example usage with dummy data
    whisper_out = {"transcript": "Hello world", "confidence": 0.85}
    speech_out = {"clarity_score": 0.7, "pause_ratio": 0.2, "confidence_score": 0.75}
    emotion_out = {"happy": 0.4, "neutral": 0.5, "sad": 0.1}
    relevance_out = {"relevance_score": 0.8}

    result = aggregate_scores(whisper_out, speech_out, emotion_out, relevance_out)
    print(result)