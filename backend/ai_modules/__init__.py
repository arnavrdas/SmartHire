"""
AI Modules Package

Individual modules:
  speech_to_text  — Whisper transcription
  speech_analysis — Librosa audio features
  emotion_analysis — MediaPipe facial landmark stability
  answer_relevance — SentenceTransformer cosine similarity
  score_aggregator — Weighted score aggregation

All heavy libraries (whisper, librosa, mediapipe, sentence-transformers)
are imported lazily inside each module's functions, not at module level.
Import this package at startup is safe even if the libraries aren't installed.
"""

# No top-level re-exports — import directly from the submodule when needed:
#   from ai_modules.speech_to_text import transcribe_audio
