import librosa
import numpy as np
from pathlib import Path

def analyze_speech(file_path: str) -> dict:
    """
    Analyze speech clarity and confidence using Librosa.
    
    Args:
        file_path (str): Path to the audio file (.wav, .mp3, etc.)
    
    Returns:
        dict: Clarity score, speaking rate, pause ratio
    """
    audio_file = Path(file_path)
    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    # Load audio
    y, sr = librosa.load(str(audio_file), sr=None)

    # Extract features
    rms = librosa.feature.rms(y=y)[0]              # Root Mean Square energy
    zcr = librosa.feature.zero_crossing_rate(y)[0] # Zero Crossing Rate
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr) # Speaking tempo estimate

    # Calculate pause ratio (silence vs speech)
    silence_threshold = np.mean(rms) * 0.3
    silence_frames = np.sum(rms < silence_threshold)
    pause_ratio = silence_frames / len(rms)

    # Confidence heuristic: higher RMS + lower pause ratio → better confidence
    clarity_score = float(np.mean(rms))
    confidence_score = float((np.mean(rms) * (1 - pause_ratio)))

    return {
        "clarity_score": round(clarity_score, 3),
        "speaking_rate": round(tempo, 2),
        "pause_ratio": round(pause_ratio, 3),
        "confidence_score": round(confidence_score, 3)
    }

if __name__ == "__main__":
    # Example usage
    output = analyze_speech("sample_audio.wav")
    print(output)
