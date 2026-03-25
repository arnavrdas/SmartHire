"""
AI Modules Package
Contains individual modules for:
- speech_to_text (Whisper)
- speech_analysis (Librosa)
- emotion_analysis (DeepFace)
- answer_relevance (Sentence-Transformers)
- score_aggregator (Weighted scoring)
"""

# Explicit imports for convenience
from .speech_to_text import transcribe_audio
from .speech_analysis import analyze_speech
from .emotion_analysis import analyze_emotions
from .answer_relevance import evaluate_answer_relevance
from .score_aggregator import aggregate_scores