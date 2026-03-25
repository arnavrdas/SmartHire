from deepface import DeepFace
import cv2
import os
from pathlib import Path

def analyze_emotions(video_path: str, frame_interval: int = 30) -> dict:
    """
    Analyze emotions from video frames using DeepFace.
    
    Args:
        video_path (str): Path to the candidate's video file (.mp4, .avi, etc.)
        frame_interval (int): Extract every Nth frame for analysis
    
    Returns:
        dict: Aggregated emotion scores across frames
    """
    video_file = Path(video_path)
    if not video_file.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    cap = cv2.VideoCapture(str(video_file))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    emotions_summary = {}

    frame_idx = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            try:
                analysis = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
                emotions = analysis[0]['emotion'] if isinstance(analysis, list) else analysis['emotion']

                # Aggregate scores
                for emotion, score in emotions.items():
                    emotions_summary[emotion] = emotions_summary.get(emotion, 0) + score
            except Exception as e:
                print(f"Frame {frame_idx} skipped due to error: {e}")

        frame_idx += 1

    cap.release()

    # Normalize scores
    total = sum(emotions_summary.values())
    if total > 0:
        emotions_summary = {k: round(v / total, 3) for k, v in emotions_summary.items()}

    return emotions_summary

if __name__ == "__main__":
    # Example usage
    output = analyze_emotions("sample_video.mp4")
    print(output)
