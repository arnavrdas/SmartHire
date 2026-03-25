import pytest
from ai_modules.speech_analysis import analyze_speech

def test_analyze_speech_file_not_found():
    with pytest.raises(FileNotFoundError):
        analyze_speech("non_existent.wav")

def test_analyze_speech_valid(monkeypatch):
    # Mock librosa.load
    monkeypatch.setattr("librosa.load", lambda f, sr=None: ([0.1, 0.2, 0.3], 22050))
    monkeypatch.setattr("librosa.feature.rms", lambda y: [[0.1, 0.2, 0.3]])
    monkeypatch.setattr("librosa.feature.zero_crossing_rate", lambda y: [[0.1, 0.2, 0.3]])
    monkeypatch.setattr("librosa.beat.beat_track", lambda y, sr: (120, None))

    result = analyze_speech("sample_audio.wav")
    assert "clarity_score" in result
    assert "confidence_score" in result