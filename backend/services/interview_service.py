"""
services/interview_service.py
------------------------------
Orchestrates the AI modules into a single analysis pipeline.

PERFORMANCE NOTES
-----------------
The four AI steps that were previously run sequentially are now run in parallel
using Python's ThreadPoolExecutor.  Each step is independent (audio, video, text
have no dependency on each other), so they can run at the same time:

  Thread 1:  ffmpeg convert → Whisper transcription → Librosa speech analysis
  Thread 2:  MediaPipe emotion analysis (reads video independently)
  Thread 3:  SBERT answer relevance (pure text, no files needed)

  Old time (sequential): ~40-60s on CPU
  New time (parallel):   ~15-25s on CPU  (limited by slowest thread = Whisper)

Additional speedups applied:
  - Whisper 'tiny' model (3x faster than 'base', ~85-90% accuracy on clear English)
  - fp16=False explicitly set to avoid the UserWarning on CPU
  - condition_on_previous_text=False for faster decode

SCORING CRITERIA
----------------
  RELEVANCE (35%):   Per-question NLP scoring — topic extraction + cosine similarity
                     + cross-encoder reranking.  Average over answered questions only.
  CONFIDENCE (25%):  Librosa — RMS energy × (1 - pause_ratio).
  EMOTION (20%):     MediaPipe FaceMesh landmark stability (EAR, brow, MAR).
  COMMUNICATION (20%): Whisper log-prob confidence + Librosa clarity + spectral stability.
  OVERALL:           Weighted sum of the four above.
  SHORTLIST:         overall >= 72.
"""

import subprocess
import shutil as _shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def _ffmpeg_available() -> bool:
    return _shutil.which("ffmpeg") is not None


def _convert_to_wav(src: str, dst: str) -> bool:
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", src, "-ar", "16000", "-ac", "1", "-f", "wav", dst],
            capture_output=True,
            timeout=60,
        )
        return result.returncode == 0 and Path(dst).exists()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _run_audio_pipeline(audio_path: str) -> tuple:
    """
    Thread 1: convert webm → wav, then run Whisper + Librosa.
    Returns (whisper_out, speech_out, wav_path, audio_ok).
    """
    wav_path  = str(Path(audio_path).with_suffix(".wav"))
    audio_ok  = _ffmpeg_available() and _convert_to_wav(audio_path, wav_path)

    if audio_ok:
        try:
            from ai_modules.speech_to_text import transcribe_audio
            whisper_out = transcribe_audio(wav_path)
        except Exception:
            whisper_out = _neutral_whisper()

        try:
            from ai_modules.speech_analysis import analyze_speech
            speech_out = analyze_speech(wav_path, word_count=whisper_out.get("word_count", 0))
        except Exception:
            speech_out = _neutral_speech()
    else:
        whisper_out = _neutral_whisper()
        speech_out  = _neutral_speech()

    return whisper_out, speech_out, wav_path, audio_ok


def _run_emotion_pipeline(video_path: str) -> dict:
    """Thread 2: MediaPipe emotion analysis from video."""
    try:
        from ai_modules.emotion_analysis import analyze_emotions
        return analyze_emotions(video_path)
    except Exception:
        return {"stability_score": 0.6}


def _run_relevance_pipeline(candidate_answers: list, questions: list) -> dict:
    """Thread 3: SBERT answer relevance (pure text, no files needed)."""
    clean_answers = [
        a if (a and not a.startswith("[")) else ""
        for a in candidate_answers
    ]
    try:
        from ai_modules.answer_relevance import evaluate_answer_relevance
        return evaluate_answer_relevance(clean_answers, list(questions))
    except Exception:
        return {"relevance_score": 0.5, "per_question": [], "answered_count": 0}


def run_analysis(
    audio_path: str,
    video_path: str,
    candidate_answers: list,
    questions: list,
) -> dict:
    """
    Run the full AI pipeline for one interview submission.

    Runs audio (Whisper+Librosa), video (MediaPipe), and text (SBERT)
    pipelines in parallel using threads.

    Returns:
        { overall, relevance, confidence, emotion, communication }
        All values are integers 0-100.
    """
    try:
        from ai_modules.score_aggregator import aggregate_scores
    except ImportError as e:
        raise RuntimeError(
            f"AI library not installed: {e}. Run: pip install -r requirements.txt"
        ) from e

    # ── Run all three pipelines in parallel ───────────────────────────────────
    whisper_out = _neutral_whisper()
    speech_out  = _neutral_speech()
    emotion_out = {"stability_score": 0.6}
    relevance_out = {"relevance_score": 0.5, "per_question": [], "answered_count": 0}
    wav_path = None
    audio_ok = False

    with ThreadPoolExecutor(max_workers=3) as pool:
        fut_audio    = pool.submit(_run_audio_pipeline,    audio_path)
        fut_emotion  = pool.submit(_run_emotion_pipeline,  video_path)
        fut_relevance = pool.submit(_run_relevance_pipeline, candidate_answers, questions)

        for fut in as_completed([fut_audio, fut_emotion, fut_relevance]):
            try:
                result = fut.result()
                if fut is fut_audio:
                    whisper_out, speech_out, wav_path, audio_ok = result
                elif fut is fut_emotion:
                    emotion_out = result
                elif fut is fut_relevance:
                    relevance_out = result
            except Exception:
                pass   # each pipeline already returns neutral values on failure

    # ── Aggregate and normalise ───────────────────────────────────────────────
    try:
        raw = aggregate_scores(whisper_out, speech_out, emotion_out, relevance_out)
    except Exception:
        raw = {}

    scores = _normalise(raw, speech_out, whisper_out, relevance_out, emotion_out)

    # ── Cleanup wav ───────────────────────────────────────────────────────────
    if audio_ok and wav_path:
        try:
            Path(wav_path).unlink(missing_ok=True)
        except Exception:
            pass

    return scores


def _neutral_whisper() -> dict:
    return {"transcript": "", "confidence": 0.75, "segments": [], "word_count": 0}


def _neutral_speech() -> dict:
    return {
        "clarity_score":      0.04,
        "speaking_rate":      130.0,
        "pause_ratio":        0.25,
        "confidence_score":   0.04,
        "spectral_stability": 0.7,
    }


def _normalise(aggregated, speech_out, whisper_out, relevance_out, emotion_out) -> dict:
    def to100(v: float, lo: float = 0.0, hi: float = 1.0) -> int:
        if hi == lo:
            return 50
        pct = (float(v) - lo) / (hi - lo)
        return max(0, min(100, round(pct * 100)))

    relevance  = to100(relevance_out.get("relevance_score", 0.5))

    raw_conf   = speech_out.get("confidence_score", 0.04)
    confidence = to100(raw_conf, lo=0.0, hi=0.10)
    confidence = max(30, min(95, confidence))

    emotion = to100(emotion_out.get("stability_score", 0.6))
    emotion = max(30, min(95, emotion))

    whisper_conf       = whisper_out.get("confidence",         0.75)
    clarity            = speech_out.get("clarity_score",       0.04)
    spectral_stability = speech_out.get("spectral_stability",  0.70)
    clarity_pct        = min(1.0, clarity / 0.10)
    comm_raw           = whisper_conf * 0.50 + clarity_pct * 0.30 + spectral_stability * 0.20
    communication      = to100(comm_raw)
    communication      = max(30, min(95, communication))

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