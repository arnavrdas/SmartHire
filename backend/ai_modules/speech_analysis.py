"""
ai_modules/speech_analysis.py
--------------------------------
Analyse speech confidence from an audio waveform using Librosa.

WHAT IS ACTUALLY MEASURED
--------------------------

  RMS Energy (clarity / loudness)
  ---------------------------------
  Root Mean Square energy of the audio signal.  Measures how loud and
  projected the candidate's voice is.  A soft-spoken or muffled recording
  scores lower.  Typical range for a laptop mic: 0.01-0.12.

  Pause Ratio (speaking fluency)
  --------------------------------
  Fraction of audio frames that are near-silent (< 30% of mean RMS).
  Frequent long pauses indicate hesitation or nervousness.
  A good speaker: pause_ratio ≈ 0.15-0.35 (some pauses are natural).
  Very high pause_ratio (> 0.60) = lots of silence = nervous or unprepared.

  Speaking Rate (fluency proxy)
  ------------------------------
  Words per minute estimated from the Whisper word_count and audio duration.
  This replaces the old beat_track() call, which measured MUSICAL tempo and
  was completely wrong for speech (it would return ~120 BPM regardless).
  Typical comfortable speaking rate: 120-160 wpm.
  Very fast (>200 wpm) or very slow (<80 wpm) both indicate nervousness.

  Spectral Centroid Variance (vocal stability)
  ----------------------------------------------
  The spectral centroid is the "centre of mass" of the frequency spectrum —
  roughly, the perceived brightness of the voice.  High variance means the
  voice pitch/brightness fluctuates a lot (nervous, shaky voice).
  Low variance = steady, controlled voice.

  Confidence Score (composite)
  ------------------------------
  confidence_score = RMS_mean × (1 - pause_ratio)
  This is the primary signal passed to the scoring pipeline.
  Calibrated so a typical good speaker scores ~0.05-0.07 (maps to ~65/100).
"""

from pathlib import Path


def analyze_speech(file_path: str, word_count: int = 0) -> dict:
    """
    Analyse speech characteristics from an audio file.

    Args:
        file_path:  Path to a wav/mp3/webm file.
        word_count: Optional word count from Whisper transcript.
                    Used to compute a proper words-per-minute speaking rate.

    Returns:
        {
          "clarity_score":       float,   RMS energy (0-1 range after clamp)
          "speaking_rate":       float,   words per minute (0 if unknown)
          "pause_ratio":         float,   fraction of silence frames
          "confidence_score":    float,   primary composite score
          "spectral_stability":  float,   0-1 (1 = steady voice)
        }
    """
    neutral = {
        "clarity_score":      0.04,
        "speaking_rate":      130.0,
        "pause_ratio":        0.25,
        "confidence_score":   0.04,
        "spectral_stability": 0.7,
    }

    if not Path(file_path).exists():
        return neutral

    try:
        import librosa
        import numpy as np

        y, sr = librosa.load(str(file_path), sr=None)

        if len(y) == 0:
            return neutral

        duration_sec = len(y) / sr

        # ── RMS Energy ────────────────────────────────────────────────────────
        rms = librosa.feature.rms(y=y)[0]
        rms_mean = float(np.mean(rms))

        # ── Pause Detection ───────────────────────────────────────────────────
        # A frame is "silent" if its energy is below 30% of the mean RMS.
        # This threshold works reasonably across different mic gains.
        silence_threshold = rms_mean * 0.30
        silence_frames    = int(np.sum(rms < silence_threshold))
        pause_ratio       = silence_frames / max(len(rms), 1)

        # ── Speaking Rate (words per minute) ──────────────────────────────────
        # Use Whisper word_count if provided; otherwise estimate from voiced
        # frame count (rough approximation).
        if word_count > 0 and duration_sec > 0:
            speaking_rate = (word_count / duration_sec) * 60.0
        else:
            # Estimate: voiced frames × typical syllables-per-frame rate
            voiced_frames = len(rms) - silence_frames
            voiced_sec    = voiced_frames * (512 / sr)  # default hop_length=512
            # Average ~3 syllables per second ≈ ~2 words per second
            speaking_rate = (voiced_sec * 2.0 / max(duration_sec, 1)) * 60.0
        speaking_rate = float(np.clip(speaking_rate, 0, 400))

        # ── Spectral Centroid Variance (vocal steadiness) ─────────────────────
        # Only over voiced frames to avoid silence skewing the measurement
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        voiced_mask = rms > silence_threshold
        # Align lengths (centroid and rms may differ by 1 frame)
        min_len = min(len(centroid), len(voiced_mask))
        voiced_centroid = centroid[:min_len][voiced_mask[:min_len]]

        if len(voiced_centroid) > 5:
            cv = float(np.std(voiced_centroid) / (np.mean(voiced_centroid) + 1e-6))
            # CV > 0.5 = very variable voice; map [0, 0.5] → [1, 0]
            spectral_stability = float(np.clip(1.0 - cv / 0.5, 0.0, 1.0))
        else:
            spectral_stability = 0.7  # neutral

        # ── Composite Confidence ──────────────────────────────────────────────
        # The primary signal: louder + fewer pauses = more confident
        confidence_score = rms_mean * (1.0 - pause_ratio)

        return {
            "clarity_score":      round(rms_mean,          4),
            "speaking_rate":      round(speaking_rate,      1),
            "pause_ratio":        round(pause_ratio,        3),
            "confidence_score":   round(confidence_score,   4),
            "spectral_stability": round(spectral_stability, 3),
        }

    except Exception:
        return neutral


if __name__ == "__main__":
    import sys
    result = analyze_speech(sys.argv[1] if len(sys.argv) > 1 else "sample.wav")
    for k, v in result.items():
        print(f"  {k}: {v}")