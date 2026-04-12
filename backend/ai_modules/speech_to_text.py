"""
ai_modules/speech_to_text.py
------------------------------
Transcribe audio using OpenAI Whisper and extract real confidence.

Whisper outputs per-segment log probabilities.  We use these to compute
a real confidence score instead of the old hardcoded 0.9.

Confidence is derived from:
  - avg_logprob: average log-probability of recognised tokens per segment
    (higher = Whisper is more sure about what was said)
  - no_speech_prob: probability that the segment contains no speech
    (higher = silence or noise, lower = real speech)

  per_segment_confidence = exp(avg_logprob) × (1 - no_speech_prob)
  final_confidence = mean of all segment confidences

This means:
  - Clear speech, correct words → confidence near 0.9-1.0
  - Mumbled / accented / noisy → confidence 0.5-0.8
  - Silence or heavy noise     → confidence near 0.0-0.3
"""

from pathlib import Path
import math

_model = None  # cached after first load


def _get_model():
    global _model
    if _model is None:
        import whisper
        _model = whisper.load_model("base")
    return _model


def transcribe_audio(file_path: str) -> dict:
    """
    Transcribe an audio file using Whisper.

    Returns:
        {
          "transcript":  str,         — full transcription text
          "confidence":  float 0-1,   — real per-segment confidence (NOT hardcoded)
          "segments":    list[dict],  — per-segment detail (start, end, text, conf)
          "word_count":  int,         — number of words recognised
        }
    """
    if not Path(file_path).exists():
        return {"transcript": "", "confidence": 0.0, "segments": [], "word_count": 0}

    try:
        model  = _get_model()
        result = model.transcribe(
            str(file_path),
            language="en",          # force English — avoids misdetection
            verbose=False,
        )

        transcript = result.get("text", "").strip()
        segments   = result.get("segments", [])

        # ── Real confidence from segment-level log probabilities ──────────────
        seg_confidences = []
        seg_details     = []

        for seg in segments:
            avg_logprob    = seg.get("avg_logprob",    -1.0)
            no_speech_prob = seg.get("no_speech_prob",  0.5)

            # exp(avg_logprob) converts log-prob to a 0-1 probability
            # Clamp logprob to reasonable range to avoid exp overflow
            token_conf = math.exp(max(avg_logprob, -3.0))

            # Down-weight segments where Whisper thinks there's no speech
            seg_conf = token_conf * (1.0 - no_speech_prob)
            seg_confidences.append(seg_conf)

            seg_details.append({
                "start": round(seg.get("start", 0), 2),
                "end":   round(seg.get("end",   0), 2),
                "text":  seg.get("text", "").strip(),
                "conf":  round(seg_conf, 3),
            })

        if seg_confidences:
            confidence = sum(seg_confidences) / len(seg_confidences)
        else:
            # No segments = nothing heard — but we did get a transcript string,
            # which means Whisper ran without segment info (shouldn't happen
            # with base model but handle it gracefully)
            confidence = 0.85 if transcript else 0.0

        # Clamp to [0, 1]
        confidence = max(0.0, min(1.0, confidence))

        return {
            "transcript":  transcript,
            "confidence":  round(confidence, 4),
            "segments":    seg_details,
            "word_count":  len(transcript.split()) if transcript else 0,
        }

    except Exception as e:
        return {"transcript": "", "confidence": 0.0, "segments": [], "word_count": 0}


if __name__ == "__main__":
    import sys
    result = transcribe_audio(sys.argv[1] if len(sys.argv) > 1 else "sample.wav")
    print(f"Transcript:  {result['transcript']}")
    print(f"Confidence:  {result['confidence']}")
    print(f"Word count:  {result['word_count']}")
    for s in result["segments"]:
        print(f"  [{s['start']}s-{s['end']}s] (conf {s['conf']}) {s['text']}")