import pytest
from ai_modules.speech_to_text import transcribe_audio

def test_transcribe_audio_file_not_found():
    with pytest.raises(FileNotFoundError):
        transcribe_audio("non_existent.wav")

def test_transcribe_audio_valid(monkeypatch):
    # Mock Whisper output
    def mock_transcribe(file_path):
        return {"text": "Hello world"}
    monkeypatch.setattr("whisper.load_model", lambda _: type("MockModel", (), {"transcribe": mock_transcribe}))
    
    result = transcribe_audio("sample_audio.wav")
    assert "transcript" in result
    assert "confidence" in result