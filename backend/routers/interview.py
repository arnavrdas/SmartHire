"""
routers/interview.py
---------------------
POST /interview/analyse — receive audio + video + answers, run AI pipeline.
"""

import json
import shutil
import subprocess
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(tags=["Interview"])

BACKEND_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR  = BACKEND_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _ffmpeg_available() -> bool:
    import shutil as sh
    return sh.which("ffmpeg") is not None


def _convert_video_to_mp4(src: Path, dst: Path) -> bool:
    """
    Convert browser .webm video to .mp4 so OpenCV can decode it on Windows.
    OpenCV on Windows ships without the VP8/VP9 decoder — it opens the file
    but reads 0 frames, producing the 'EBML header parsing failed' error.
    ffmpeg re-encodes to H.264/AAC which OpenCV handles natively everywhere.
    Returns True on success.
    """
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(src),
                "-c:v", "libx264", "-preset", "ultrafast",
                "-c:a", "aac",
                str(dst),
            ],
            capture_output=True,
            timeout=120,
        )
        return result.returncode == 0 and dst.exists() and dst.stat().st_size > 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


@router.post("/analyse")
async def analyse_interview(
    audio:     UploadFile,
    video:     UploadFile,
    answers:   str = Form(...),
    questions: str = Form(...),
):
    try:
        answers_list   = json.loads(answers)
        questions_list = json.loads(questions)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=422, detail="answers and questions must be valid JSON arrays")

    if not isinstance(answers_list, list) or not isinstance(questions_list, list):
        raise HTTPException(status_code=422, detail="answers and questions must be JSON arrays")

    run_id     = uuid.uuid4().hex
    audio_path = UPLOAD_DIR / f"{run_id}_audio.webm"
    video_path = UPLOAD_DIR / f"{run_id}_video.webm"
    video_mp4  = UPLOAD_DIR / f"{run_id}_video.mp4"   # converted for OpenCV

    try:
        with open(audio_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)
        with open(video_path, "wb") as f:
            shutil.copyfileobj(video.file, f)
    except Exception as e:
        _safe_delete(audio_path, video_path, video_mp4)
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {e}")

    # ── Convert video webm → mp4 so OpenCV can decode it on Windows ──────────
    # If ffmpeg succeeds we pass the mp4; otherwise fall back to raw webm
    # (works on Linux/macOS where OpenCV ships with the VP8 decoder).
    if _ffmpeg_available() and _convert_video_to_mp4(video_path, video_mp4):
        analysis_video = str(video_mp4)
    else:
        analysis_video = str(video_path)

    try:
        from services.interview_service import run_analysis
        scores = run_analysis(
            audio_path=str(audio_path),
            video_path=analysis_video,
            candidate_answers=answers_list,
            questions=questions_list,
        )
    except RuntimeError as e:
        _safe_delete(audio_path, video_path, video_mp4)
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        _safe_delete(audio_path, video_path, video_mp4)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    _safe_delete(audio_path, video_path, video_mp4)
    return JSONResponse(content=scores)


def _safe_delete(*paths: Path) -> None:
    for p in paths:
        try:
            p.unlink(missing_ok=True)
        except Exception:
            pass


@router.get("/{interview_id}/results")
async def get_results(interview_id: str):
    raise HTTPException(
        status_code=501,
        detail="Async result polling not yet implemented (Phase 3).",
    )