from __future__ import annotations

import os
import shutil

from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse

from app.schemas.job import (
    UploadResponse,
    AnalysisResponse,
    TranscribeRequest,
    JobStatusResponse,
    JobResultResponse,
    JobStatus,
    TranscriptionMode,
    IMPLEMENTED_MODES,
)
from app.services import audio_processor
from app.services.job_manager import job_manager, UPLOADS_DIR

router = APIRouter(prefix="/api")

ALL_MODES = [m.value for m in TranscriptionMode]
IMPLEMENTED = {m.value for m in IMPLEMENTED_MODES}
COMING_SOON = [m for m in ALL_MODES if m not in IMPLEMENTED]


@router.post("/upload", response_model=UploadResponse)
async def upload_audio(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No filename provided.")

    try:
        audio_processor.validate_extension(file.filename)
    except audio_processor.AudioValidationError as exc:
        raise HTTPException(400, str(exc))

    raw_bytes = await file.read()
    try:
        audio_processor.validate_size(len(raw_bytes))
    except audio_processor.AudioValidationError as exc:
        raise HTTPException(400, str(exc))

    tmp_name = f"{os.urandom(8).hex()}_{file.filename}"
    upload_path = os.path.join(UPLOADS_DIR, tmp_name)
    with open(upload_path, "wb") as f:
        f.write(raw_bytes)

    try:
        audio_processor.ffprobe_inspect(upload_path)
        probe = audio_processor.ffprobe_inspect(upload_path)
        audio_processor.validate_duration(probe)
    except audio_processor.AudioValidationError as exc:
        os.remove(upload_path)
        raise HTTPException(400, str(exc))

    song_title = os.path.splitext(file.filename)[0]
    job = job_manager.create_job(upload_path, file.filename, song_title)
    job_manager.run_analysis_async(job.job_id)

    return UploadResponse(job_id=job.job_id, filename=file.filename, status=JobStatus.ANALYZING)


@router.get("/jobs/{job_id}/analysis", response_model=AnalysisResponse)
async def get_analysis(job_id: str):
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    if job.status == JobStatus.FAILED:
        raise HTTPException(422, job.error or "Analysis failed.")
    if job.status in (JobStatus.PENDING, JobStatus.ANALYZING):
        raise HTTPException(202, "Analysis still in progress. Poll again shortly.")

    return AnalysisResponse(
        job_id=job.job_id,
        status=job.status,
        duration_seconds=job.duration_seconds or 0.0,
        tempo_bpm=job.tempo_bpm,
        key=job.key,
        time_signature=job.time_signature,
        time_signature_confidence=job.time_signature_confidence,
        is_silent=job.is_silent,
        available_modes=sorted(IMPLEMENTED),
        coming_soon_modes=sorted(COMING_SOON),
    )


@router.post("/transcribe/{job_id}", response_model=JobStatusResponse)
async def start_transcription(job_id: str, req: TranscribeRequest):
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    if job.status != JobStatus.ANALYZED:
        raise HTTPException(409, f"Job is not ready for transcription (status={job.status.value}).")

    if req.mode not in IMPLEMENTED_MODES:
        raise HTTPException(
            501,
            f"Mode '{req.mode.value}' is Coming Soon. Available now: "
            f"{', '.join(sorted(IMPLEMENTED))}.",
        )

    job_manager.run_transcription(
        job_id,
        mode=req.mode,
        quantization=req.quantization,
        remove_duplicates=req.remove_duplicate_notes,
        remove_short_noise=req.remove_short_noise,
        engine=req.engine,
    )
    return JobStatusResponse(
        job_id=job.job_id, status=JobStatus.TRANSCRIBING, progress=job.progress, current_step=job.current_step
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        current_step=job.current_step,
        error=job.error,
    )


@router.get("/jobs/{job_id}/result", response_model=JobResultResponse)
async def get_job_result(job_id: str):
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    if job.status == JobStatus.FAILED:
        raise HTTPException(422, job.error or "Job failed.")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(202, "Job not completed yet.")

    return JobResultResponse(
        job_id=job.job_id,
        status=job.status,
        song_title=job.song_title,
        duration_seconds=job.duration_seconds or 0.0,
        tempo_bpm=job.tempo_bpm,
        key=job.key,
        time_signature=job.time_signature,
        note_count=job.note_count,
        musicxml_url=f"/api/jobs/{job.job_id}/musicxml",
        midi_url=f"/api/jobs/{job.job_id}/midi",
        engine_used=job.engine_used or "unknown",
    )


@router.get("/jobs/{job_id}/musicxml")
async def download_musicxml(job_id: str):
    job = job_manager.get(job_id)
    if not job or not job.musicxml_path or not os.path.exists(job.musicxml_path):
        raise HTTPException(404, "MusicXML not available for this job.")
    filename = f"{job.song_title}.musicxml"
    return FileResponse(job.musicxml_path, filename=filename, media_type="application/vnd.recordare.musicxml+xml")


@router.get("/jobs/{job_id}/midi")
async def download_midi(job_id: str):
    job = job_manager.get(job_id)
    if not job or not job.midi_path or not os.path.exists(job.midi_path):
        raise HTTPException(404, "MIDI not available for this job.")
    filename = f"{job.song_title}.mid"
    return FileResponse(job.midi_path, filename=filename, media_type="audio/midi")


@router.delete("/jobs/{job_id}")
async def delete_job_files(job_id: str):
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    job_manager.cleanup_job_files(job_id)
    return {"job_id": job_id, "temp_files_removed": True}
