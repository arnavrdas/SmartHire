from sentence_transformers import SentenceTransformer
import whisper

def load_sentence_model(model_name: str = "all-MiniLM-L6-v2"):
    """
    Load Sentence-Transformer model.
    """
    return SentenceTransformer(model_name)

def load_whisper_model(model_size: str = "base"):
    """
    Load Whisper model.
    """
    return whisper.load_model(model_size)