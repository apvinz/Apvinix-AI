from __future__ import annotations

from enum import Enum
from typing import Optional, List

from pydantic import BaseModel


class JobStatus(str, Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    TRANSCRIBING = "transcribing"
    CLEANING_MIDI = "cleaning_midi"
    BUILDING_SCORE = "building_score"
    COMPLETED = "completed"
    FAILED = "failed"


class TranscriptionMode(str, Enum):
    MELODY = "melody"
    MELODY_CHORDS = "melody_chords"  # Coming Soon
    PIANO = "piano"  # Coming Soon
    FULL_SONG = "full_song"  # Coming Soon


IMPLEMENTED_MODES = {TranscriptionMode.MELODY}


class UploadResponse(BaseModel):
    job_id: str
    filename: str
    status: JobStatus


class AnalysisResponse(BaseModel):
    job_id: str
    status: JobStatus
    duration_seconds: float
    tempo_bpm: Optional[float]
    key: Optional[str]
    time_signature: str
    time_signature_confidence: Optional[str]
    is_silent: bool
    available_modes: List[str]
    coming_soon_modes: List[str]


class TranscribeRequest(BaseModel):
    mode: TranscriptionMode = TranscriptionMode.MELODY
    quantization: str = "auto"  # auto | 1/4 | 1/8 | 1/16 | 1/32
    remove_duplicate_notes: bool = True
    remove_short_noise: bool = True
    engine: str = "pyin"  # pyin | basic_pitch


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int  # 0-100, real step-based progress, not fabricated
    current_step: str
    error: Optional[str] = None


class JobResultResponse(BaseModel):
    job_id: str
    status: JobStatus
    song_title: str
    duration_seconds: float
    tempo_bpm: Optional[float]
    key: Optional[str]
    time_signature: str
    note_count: int
    musicxml_url: str
    midi_url: str
    engine_used: str
