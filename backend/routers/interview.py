"""
routers/interview.py
---------------------
POST /interview/analyse   — receive audio + video + answers, run AI pipeline,
                            return scores as { overall, relevance, confidence,
                            emotion, communication } (all 0-100 ints).
"""

import json
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(tags=["Interview"])

# ── Absolute path so it works regardless of where uvicorn is launched from ────
# __file__ is  .../backend/routers/interview.py
# .parent       → .../backend/routers/
# .parent.parent → .../backend/
BACKEND_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR  = BACKEND_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/analyse")
async def analyse_interview(
    audio:     UploadFile,
    video:     UploadFile,
    answers:   str = Form(...),
    questions: str = Form(...),
):
    """
    Run the AI analysis pipeline on a completed interview recording.

    Multipart body:
        audio     — webm recorded by the browser (audio track used by Whisper)
        video     — webm recorded by the browser (video track used by MediaPipe)
        answers   — JSON array of answer strings
        questions — JSON array of question strings

    Returns:
        { overall, relevance, confidence, emotion, communication }
        All values are integers 0-100.
    """
    # ── Parse JSON form fields ────────────────────────────────────────────────
    try:
        answers_list   = json.loads(answers)
        questions_list = json.loads(questions)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(
            status_code=422,
            detail="answers and questions must be valid JSON arrays",
        )

    if not isinstance(answers_list, list) or not isinstance(questions_list, list):
        raise HTTPException(
            status_code=422,
            detail="answers and questions must be JSON arrays",
        )

    # ── Save uploaded files with absolute paths ───────────────────────────────
    run_id     = uuid.uuid4().hex
    audio_path = UPLOAD_DIR / f"{run_id}_audio.webm"
    video_path = UPLOAD_DIR / f"{run_id}_video.webm"

    try:
        with open(audio_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)
        with open(video_path, "wb") as f:
            shutil.copyfileobj(video.file, f)
    except Exception as e:
        _safe_delete(audio_path, video_path)
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {e}")

    # ── Run pipeline, then clean up ───────────────────────────────────────────
    # NOTE: do NOT put cleanup in a finally block — the pipeline reads the files
    # and finally would delete them before analysis finishes on slow machines.
    try:
        from services.interview_service import run_analysis

        scores = run_analysis(
            audio_path=str(audio_path),
            video_path=str(video_path),
            candidate_answers=answers_list,
            questions=questions_list,
        )
    except RuntimeError as e:
        _safe_delete(audio_path, video_path)
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        _safe_delete(audio_path, video_path)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    # Clean up only after the pipeline has fully returned
    _safe_delete(audio_path, video_path)
    return JSONResponse(content=scores)


def _safe_delete(*paths: Path) -> None:
    for p in paths:
        try:
            p.unlink(missing_ok=True)
        except Exception:
            pass  # best-effort cleanup — never crash on delete failure


@router.get("/{interview_id}/results")
async def get_results(interview_id: str):
    raise HTTPException(
        status_code=501,
        detail="Async result polling not yet implemented (Phase 3). "
               "Use POST /interview/analyse for synchronous analysis.",
    )