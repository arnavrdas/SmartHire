import librosa
import numpy as np

def load_audio(file_path: str, sr: int = None):
    """
    Load audio file using Librosa.
    Args:
        file_path (str): Path to audio file
        sr (int): Sampling rate (None = original)
    Returns:
        tuple: (waveform, sampling_rate)
    """
    y, sr = librosa.load(file_path, sr=sr)
    return y, sr

def normalize_audio(y: np.ndarray) -> np.ndarray:
    """
    Normalize audio waveform to range [-1, 1].
    """
    return y / np.max(np.abs(y))