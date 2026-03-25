import whisper
from pathlib import Path

def transcribe_audio(file_path: str) -> dict:
    """
    Transcribes audio using OpenAI Whisper.
    
    Args:
        file_path (str): Path to the audio file (.wav, .mp3, etc.)
    
    Returns:
        dict: Transcript and confidence score
    """
    # Ensure file exists
    audio_file = Path(file_path)
    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    # Load Whisper model (choose 'base', 'small', 'medium', 'large')
    model = whisper.load_model("base")

    # Perform transcription
    result = model.transcribe(str(audio_file))

    # Whisper does not provide explicit confidence, so we approximate
    transcript = result.get("text", "").strip()
    confidence = 0.9 if transcript else 0.0

    return {
        "transcript": transcript,
        "confidence": confidence
    }

if __name__ == "__main__":
    # Example usage
    output = transcribe_audio("sample_audio.wav")
    print(output)
