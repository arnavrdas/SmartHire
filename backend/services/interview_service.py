"""
services/interview_service.py
------------------------------
Orchestrates the AI modules into a single analysis pipeline.

SCORING CRITERIA — what each number actually means
===================================================

  RELEVANCE (35% of overall)
  ---------------------------
  Did the candidate actually answer each question?
  Scored per Q/A pair using three signals:

    Topic similarity (50%) — sentence-transformers bi-encoder cosine
      similarity between the question's core topic and the answer.
      The question is first stripped of interrogative phrasing
      ("tell me about", "explain", "describe") to extract just the topic.
      Example: "Describe a challenging project and how you overcame obstacles"
      → topic: "challenging project overcoming obstacles"
      The answer embedding is compared against this topic embedding.

    Substantiveness (30%) — is the answer long enough to be real?
      < 5 words → 0.2 (too short to mean anything)
      5-15 words → 0.5-0.7 (brief but present)
      15-50 words → 0.7-0.85 (solid)
      50+ words → 1.0 (detailed)
      Pure filler ("I don't know", "pass", "N/A") → 0.0

    Cross-encoder reranking (20%) — ms-marco-MiniLM-L-6-v2 reads the
      question and answer TOGETHER (unlike bi-encoder which reads them
      separately) for fine-grained relevance judgement.
      Falls back to 0.5 if the model isn't installed.

  Blank answers contribute 0 but don't penalise other answers.
  The final score is the average over answered questions only.

  CONFIDENCE (25% of overall)
  ----------------------------
  Measured from the audio waveform using Librosa:
    RMS energy:   average loudness of the candidate's voice
    Pause ratio:  fraction of near-silent frames (many long pauses = nervous)
    confidence_score = RMS_mean × (1 - pause_ratio)

  Calibrated so a typical clear laptop-mic speaker scores ~65/100.
  Note: a quiet microphone lowers this score regardless of actual confidence.

  EMOTION / BODY LANGUAGE (20% of overall)
  ------------------------------------------
  Measured from video frames using MediaPipe FaceMesh (468 landmarks).
  Sampled every 15 frames (~2 fps for 30fps video):
    Eye Aspect Ratio (EAR, 45% weight):
      Ratio of vertical to horizontal eye opening.
      Calm, alert eyes = stable EAR ≈ 0.25-0.35.
      Rapid blinking or squinting = high EAR variance.
    Brow raise distance (35% weight):
      Vertical distance from brow landmark to eye-top landmark.
      Raised brows = surprise or anxiety (high brow distance).
      Stable brow = neutral/positive engagement.
    Mouth Aspect Ratio (MAR, 20% weight):
      Mouth opening ratio.  Agape mouth = discomfort/surprise.
      Stable, slightly-open mouth = natural speaking posture.
  The COEFFICIENT OF VARIATION of each signal across all frames is used —
  low variation = calm and steady = higher score.

  COMMUNICATION (20% of overall)
  --------------------------------
  A composite of three signals:
    Whisper transcription confidence (50%):
      Real confidence from Whisper's segment-level log-probabilities.
      exp(avg_logprob) × (1 - no_speech_prob) per segment, averaged.
      Clear speech = high confidence; mumbling/noise = low.
    Librosa clarity (30%):
      Normalised RMS energy — how loud and projected the voice is.
    Spectral stability (20%):
      Low coefficient of variation in spectral centroid = steady voice.
      A shaky or very variable pitch lowers this score.

  OVERALL
  --------
  Weighted sum: relevance×0.35 + confidence×0.25 + emotion×0.20 + communication×0.20
"""

import subprocess
import shutil as _shutil
from pathlib import Path


def _ffmpeg_available() -> bool:
    return _shutil.which("ffmpeg") is not None


def _convert_to_wav(src: str, dst: str) -> bool:
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", src, "-ar", "16000", "-ac", "1", "-f", "wav", dst],
            capture_output=True,
            timeout=120,
        )
        return result.returncode == 0 and Path(dst).exists()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def run_analysis(
    audio_path: str,
    video_path: str,
    candidate_answers: list,
    questions: list,
) -> dict:
    """
    Run the full AI pipeline for one interview submission.

    candidate_answers: list of answer strings (one per question, in order)
    questions:         list of question strings (same order)

    Returns:
        { overall, relevance, confidence, emotion, communication }
        All values are integers 0-100.
    """
    try:
        from ai_modules.answer_relevance import evaluate_answer_relevance
        from ai_modules.score_aggregator import aggregate_scores
        from ai_modules.emotion_analysis  import analyze_emotions
    except ImportError as e:
        raise RuntimeError(
            f"AI library not installed: {e}. Run: pip install -r requirements.txt"
        ) from e

    # ── Audio: webm → wav via ffmpeg ─────────────────────────────────────────
    wav_path   = str(Path(audio_path).with_suffix(".wav"))
    has_ffmpeg = _ffmpeg_available()
    audio_ok   = False

    if has_ffmpeg:
        audio_ok = _convert_to_wav(audio_path, wav_path)

    # ── 1. Transcription (Whisper) ────────────────────────────────────────────
    if audio_ok:
        try:
            from ai_modules.speech_to_text import transcribe_audio
            whisper_out = transcribe_audio(wav_path)
        except Exception:
            whisper_out = _neutral_whisper()
    else:
        whisper_out = _neutral_whisper()

    # ── 2. Speech analysis (Librosa) ─────────────────────────────────────────
    # Pass the Whisper word_count so speech_analysis can compute a real WPM
    if audio_ok:
        try:
            from ai_modules.speech_analysis import analyze_speech
            speech_out = analyze_speech(wav_path, word_count=whisper_out.get("word_count", 0))
        except Exception:
            speech_out = _neutral_speech()
    else:
        speech_out = _neutral_speech()

    # ── 3. Emotion / body language (MediaPipe) ────────────────────────────────
    try:
        emotion_out = analyze_emotions(video_path)
    except Exception:
        emotion_out = {"stability_score": 0.6}

    # ── 4. Answer relevance (NLP — text only, no audio needed) ───────────────
    # Filter placeholder markers so they score 0 without poisoning other answers
    clean_answers = [
        a if (a and not a.startswith("[")) else ""
        for a in candidate_answers
    ]
    try:
        relevance_out = evaluate_answer_relevance(clean_answers, list(questions))
    except Exception:
        relevance_out = {"relevance_score": 0.5, "per_question": [], "answered_count": 0}

    # ── 5. Aggregate raw signals ──────────────────────────────────────────────
    try:
        raw = aggregate_scores(whisper_out, speech_out, emotion_out, relevance_out)
    except Exception:
        raw = {}

    # ── 6. Normalise to 0-100 integers ────────────────────────────────────────
    scores = _normalise(raw, speech_out, whisper_out, relevance_out, emotion_out)

    # ── Cleanup ────────────────────────────────────────────────────────────────
    try:
        if audio_ok:
            Path(wav_path).unlink(missing_ok=True)
    except Exception:
        pass

    return scores


def _neutral_whisper() -> dict:
    """Neutral Whisper output when audio decoding is unavailable."""
    return {"transcript": "", "confidence": 0.75, "segments": [], "word_count": 0}


def _neutral_speech() -> dict:
    """Neutral speech analysis output when Librosa is unavailable."""
    return {
        "clarity_score":      0.04,
        "speaking_rate":      130.0,
        "pause_ratio":        0.25,
        "confidence_score":   0.04,
        "spectral_stability": 0.7,
    }


def _normalise(aggregated, speech_out, whisper_out, relevance_out, emotion_out) -> dict:
    """
    Convert raw 0-1 module outputs to 0-100 integer scores.

    Calibration:
      relevance:    evaluate_answer_relevance returns a well-calibrated 0-1;
                    map directly.
      confidence:   RMS×(1-pause_ratio) ≈ 0.01-0.10 for typical speech;
                    scale [0, 0.10] → [0, 100], floor 30.
      emotion:      MediaPipe stability_score is already 0-1; map directly,
                    floor 30 (missing camera ≠ zero body language).
      communication: blend of Whisper confidence (real log-prob based),
                    Librosa RMS clarity, and spectral stability.
    """

    def to100(v: float, lo: float = 0.0, hi: float = 1.0) -> int:
        if hi == lo:
            return 50
        pct = (float(v) - lo) / (hi - lo)
        return max(0, min(100, round(pct * 100)))

    # Relevance
    relevance = to100(relevance_out.get("relevance_score", 0.5))

    # Confidence — RMS-based; realistic ceiling ~0.10
    raw_conf   = speech_out.get("confidence_score", 0.04)
    confidence = to100(raw_conf, lo=0.0, hi=0.10)
    confidence = max(30, min(95, confidence))

    # Emotion
    emotion = to100(emotion_out.get("stability_score", 0.6))
    emotion = max(30, min(95, emotion))

    # Communication — three signals
    whisper_conf       = whisper_out.get("confidence",         0.75)
    clarity            = speech_out.get("clarity_score",       0.04)
    spectral_stability = speech_out.get("spectral_stability",  0.70)

    clarity_pct  = min(1.0, clarity / 0.10)
    comm_raw     = (
        whisper_conf       * 0.50 +
        clarity_pct        * 0.30 +
        spectral_stability * 0.20
    )
    communication = to100(comm_raw)
    communication = max(30, min(95, communication))

    overall = round(
        relevance     * 0.35 +
        confidence    * 0.25 +
        emotion       * 0.20 +
        communication * 0.20
    )

    return {
        "relevance":     relevance,
        "confidence":    confidence,
        "emotion":       emotion,
        "communication": communication,
        "overall":       overall,
    }