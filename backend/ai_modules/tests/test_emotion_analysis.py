import pytest
from ai_modules.emotion_analysis import analyze_emotions

def test_analyze_emotions_file_not_found():
    with pytest.raises(FileNotFoundError):
        analyze_emotions("non_existent.mp4")

def test_analyze_emotions_valid(monkeypatch):
    # Mock DeepFace
    def mock_analyze(frame, actions, enforce_detection):
        return {"emotion": {"happy": 0.6, "neutral": 0.4}}
    monkeypatch.setattr("deepface.DeepFace.analyze", mock_analyze)

    # Mock cv2.VideoCapture
    class MockCap:
        def __init__(self, path): self.frames = 2
        def isOpened(self): return self.frames > 0
        def read(self): 
            if self.frames > 0:
                self.frames -= 1
                return True, "frame"
            return False, None
        def release(self): pass
        def get(self, prop): return 2
    monkeypatch.setattr("cv2.VideoCapture", MockCap)

    result = analyze_emotions("sample_video.mp4")
    assert "happy" in result
    assert "neutral" in result