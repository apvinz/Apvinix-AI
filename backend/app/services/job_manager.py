"""
job_manager.py — Job-based async processing (spec section 25).

MVP uses an in-memory dict + a background thread per job (no external
queue/broker needed to run on Windows with zero extra services). Progress
is derived from *real* pipeline steps that actually ran — never a fake
percentage ticking up on a timer.
"""
from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional

from app.schemas.job import JobStatus, TranscriptionMode
from app.services import audio_processor, analyzer as analyzer_svc
from app.services.transcription import transcribe_melody
from app.services.midi_processor import clean_note_events, write_midi_file, CleanupOptions
from app.services.musicxml_generator import build_melody_score, export_musicxml

logger = logging.getLogger("transcore.job_manager")

DATA_DIR = os.environ.get("TRANSCORE_DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "data"))
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
PROCESSING_DIR = os.path.join(DATA_DIR, "processing")
OUTPUTS_DIR = os.path.join(DATA_DIR, "outputs")
for d in (UPLOADS_DIR, PROCESSING_DIR, OUTPUTS_DIR):
    os.makedirs(d, exist_ok=True)

# Real, ordered step weights used to compute honest progress percentages.
STEP_WEIGHTS = [
    ("uploaded", 5),
    ("preprocessing", 10),
    ("analyzing", 25),
    ("transcribing", 55),
    ("cleaning_midi", 70),
    ("building_score", 85),
    ("exporting", 95),
    ("completed", 100),
]
_STEP_PROGRESS = dict(STEP_WEIGHTS)


@dataclass
class Job:
    job_id: str
    original_filename: str
    song_title: str
    upload_path: str
    normalized_path: Optional[str] = None
    status: JobStatus = JobStatus.PENDING
    current_step: str = "uploaded"
    progress: int = 5
    error: Optional[str] = None

    # analysis results
    duration_seconds: Optional[float] = None
    tempo_bpm: Optional[float] = None
    key: Optional[str] = None
    time_signature: str = "4/4"
    time_signature_confidence: Optional[str] = None
    is_silent: bool = False

    # transcription results
    mode: Optional[TranscriptionMode] = None
    engine_used: Optional[str] = None
    note_count: int = 0
    musicxml_path: Optional[str] = None
    midi_path: Optional[str] = None

    lock: threading.Lock = field(default_factory=threading.Lock)


class JobManager:
    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def create_job(self, upload_path: str, original_filename: str, song_title: str) -> Job:
        job_id = uuid.uuid4().hex[:12]
        job = Job(
            job_id=job_id,
            original_filename=original_filename,
            song_title=song_title,
            upload_path=upload_path,
        )
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def _set_step(self, job: Job, step: str, status: JobStatus) -> None:
        job.current_step = step
        job.status = status
        job.progress = _STEP_PROGRESS.get(step, job.progress)

    def run_analysis(self, job_id: str) -> None:
        job = self.get(job_id)
        if job is None:
            return
        try:
            self._set_step(job, "preprocessing", JobStatus.ANALYZING)
            normalized_path = os.path.join(PROCESSING_DIR, f"{job.job_id}.wav")
            audio_processor.normalize_to_wav(job.upload_path, normalized_path)
            job.normalized_path = normalized_path

            self._set_step(job, "analyzing", JobStatus.ANALYZING)
            result = analyzer_svc.analyze_audio(normalized_path)
            job.duration_seconds = result.duration_seconds
            job.tempo_bpm = result.tempo_bpm
            job.key = result.key
            job.time_signature = result.time_signature
            job.time_signature_confidence = result.time_signature_confidence
            job.is_silent = result.is_silent

            job.status = JobStatus.ANALYZED
            job.current_step = "analyzed"
            job.progress = _STEP_PROGRESS["analyzing"]
        except Exception as exc:
            logger.exception("Analysis failed for job %s", job_id)
            job.status = JobStatus.FAILED
            job.error = str(exc)

    def run_transcription(
        self,
        job_id: str,
        mode: TranscriptionMode,
        quantization: str,
        remove_duplicates: bool,
        remove_short_noise: bool,
        engine: str,
    ) -> None:
        job = self.get(job_id)
        if job is None:
            return

        def worker():
            try:
                if mode != TranscriptionMode.MELODY:
                    raise RuntimeError(
                        f"'{mode.value}' is Coming Soon and not yet implemented. "
                        f"Only 'melody' mode is available in this build."
                    )
                job.mode = mode

                self._set_step(job, "transcribing", JobStatus.TRANSCRIBING)
                events = transcribe_melody(job.normalized_path, engine=engine)
                job.engine_used = engine

                self._set_step(job, "cleaning_midi", JobStatus.CLEANING_MIDI)
                options = CleanupOptions(
                    remove_duplicates=remove_duplicates,
                    remove_short_noise=remove_short_noise,
                    quantize=quantization,
                )
                cleaned = clean_note_events(events, job.tempo_bpm, options)
                job.note_count = len(cleaned)

                midi_path = os.path.join(OUTPUTS_DIR, f"{job.job_id}.mid")
                write_midi_file(cleaned, job.tempo_bpm, midi_path)
                job.midi_path = midi_path

                self._set_step(job, "building_score", JobStatus.BUILDING_SCORE)
                score = build_melody_score(
                    cleaned, job.tempo_bpm, job.key, job.time_signature, job.song_title
                )

                self._set_step(job, "exporting", JobStatus.BUILDING_SCORE)
                musicxml_path = os.path.join(OUTPUTS_DIR, f"{job.job_id}.musicxml")
                export_musicxml(score, musicxml_path)
                job.musicxml_path = musicxml_path

                self._set_step(job, "completed", JobStatus.COMPLETED)
            except Exception as exc:
                logger.exception("Transcription failed for job %s", job_id)
                job.status = JobStatus.FAILED
                job.error = str(exc)

        threading.Thread(target=worker, daemon=True).start()

    def run_analysis_async(self, job_id: str) -> None:
        threading.Thread(target=self.run_analysis, args=(job_id,), daemon=True).start()

    def cleanup_job_files(self, job_id: str) -> None:
        """Deletes temporary audio for a job (spec section 26/27) while
        keeping final MusicXML/MIDI outputs available for download."""
        job = self.get(job_id)
        if not job:
            return
        for path in (job.upload_path, job.normalized_path):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    logger.warning("Could not remove temp file %s", path)


job_manager = JobManager()
