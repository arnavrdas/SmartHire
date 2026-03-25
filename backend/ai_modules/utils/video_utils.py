import cv2
from pathlib import Path

def extract_frames(video_path: str, frame_interval: int = 30):
    """
    Extract frames from video at given interval.
    Args:
        video_path (str): Path to video file
        frame_interval (int): Extract every Nth frame
    Returns:
        list: Frames as numpy arrays
    """
    video_file = Path(video_path)
    if not video_file.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    cap = cv2.VideoCapture(str(video_file))
    frames = []
    frame_idx = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % frame_interval == 0:
            frames.append(frame)
        frame_idx += 1

    cap.release()
    return frames