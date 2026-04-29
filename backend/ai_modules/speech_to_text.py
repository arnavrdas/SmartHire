"""
ai_modules/speech_to_text.py
------------------------------
Transcribe audio using OpenAI Whisper.

Model choice: 'tiny' (39M parameters) instead of 'base' (74M).
  - 'tiny'  : ~5-10s on CPU for a 5-minute recording. Accuracy ~85-90% for clear English.
  - 'base'  : ~15-30s on CPU. Accuracy ~90-93%.
  - 'small' : ~45-90s on CPU. Only worth it with a GPU.

For an interview system where candidates speak in clear English on a modern laptop,
'tiny' gives fully acceptable accuracy at roughly 3x the speed.
Switch to 'base' by changing MODEL_SIZE below if you have a GPU or need higher accuracy.
"""

from pathlib import Path
import math

MODEL_SIZE = "base"   # "tiny" | "base" | "small" — change here to upgrade
_model = None


def _get_model():
    global _model
    if _model is None:
        import whisper
        _model = whisper.load_model(MODEL_SIZE)
    return _model


def transcribe_audio(file_path: str) -> dict:
    if not Path(file_path).exists():
        return {"transcript": "", "confidence": 0.0, "segments": [], "word_count": 0}

    try:
        model  = _get_model()
        result = model.transcribe(
            str(file_path),
            language="en",
            verbose=False,
            fp16=False,          # always use FP32 on CPU — avoids the UserWarning
            condition_on_previous_text=False,  # faster, good enough for short answers
        )

        transcript = result.get("text", "").strip()
        segments   = result.get("segments", [])

        seg_confidences = []
        seg_details     = []
        for seg in segments:
            avg_logprob    = seg.get("avg_logprob",    -1.0)
            no_speech_prob = seg.get("no_speech_prob",  0.5)
            token_conf     = math.exp(max(avg_logprob, -3.0))
            seg_conf       = token_conf * (1.0 - no_speech_prob)
            seg_confidences.append(seg_conf)
            seg_details.append({
                "start": round(seg.get("start", 0), 2),
                "end":   round(seg.get("end",   0), 2),
                "text":  seg.get("text", "").strip(),
                "conf":  round(seg_conf, 3),
            })

        confidence = (sum(seg_confidences) / len(seg_confidences)) if seg_confidences else (0.85 if transcript else 0.0)
        confidence = max(0.0, min(1.0, confidence))

        return {
            "transcript":  transcript,
            "confidence":  round(confidence, 4),
            "segments":    seg_details,
            "word_count":  len(transcript.split()) if transcript else 0,
        }
    except Exception:
        return {"transcript": "", "confidence": 0.0, "segments": [], "word_count": 0}