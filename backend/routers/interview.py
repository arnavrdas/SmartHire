from fastapi import APIRouter, UploadFile, Form
from ai_modules import (
    transcribe_audio,
    analyze_speech,
    analyze_emotions,
    evaluate_answer_relevance,
    aggregate_scores
)
import shutil
import uuid
from pathlib import Path

router = APIRouter(prefix="/interview", tags=["Interview"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@router.post("/submit")
async def submit_interview(
    audio: UploadFile,
    video: UploadFile,
    candidate_answer: str = Form(...),
    expected_answer: str = Form(...)
):
    # Save files locally
    audio_path = UPLOAD_DIR / f"{uuid.uuid4()}_{audio.filename}"
    video_path = UPLOAD_DIR / f"{uuid.uuid4()}_{video.filename}"
    with open(audio_path, "wb") as f:
        shutil.copyfileobj(audio.file, f)
    with open(video_path, "wb") as f:
        shutil.copyfileobj(video.file, f)

    # Run AI modules
    whisper_out = transcribe_audio(str(audio_path))
    speech_out = analyze_speech(str(audio_path))
    emotion_out = analyze_emotions(str(video_path))
    relevance_out = evaluate_answer_relevance(candidate_answer, expected_answer)

    # Aggregate scores
    result = aggregate_scores(whisper_out, speech_out, emotion_out, relevance_out)

    # TODO: Save result in PostgreSQL (interviews table)
    # db.save_interview(candidate_id, job_id, result)

    return {"status": "processing complete", "result": result}

@router.get("/{interview_id}/results")
async def get_results(interview_id: str):
    # TODO: Fetch from PostgreSQL
    # result = db.get_interview(interview_id)
    result = {"final_score": 0.82, "breakdown": {"whisper_confidence": 0.9}}
    return result