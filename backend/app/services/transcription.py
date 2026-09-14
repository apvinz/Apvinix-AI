"""
transcription.py — Audio -> note events.

Primary engine: librosa pYIN (probabilistic YIN) monophonic pitch tracking.
This is a real, peer-reviewed MIR algorithm (Mauch & Dixon, 2014), ships
inside librosa with no extra native/GPU dependencies, and installs
reliably on Windows across Python 3.9-3.12 — which made it the more
*stable* choice than Spotify's Basic Pitch for this MVP (Basic Pitch pins
TensorFlow<2.15.1, which has no Python 3.12 wheels and is finicky on
Windows). Basic Pitch is wired in as an optional secondary engine
(engine="basic_pitch") for environments where it's installed and working —
see `basic_pitch_available()` below — and is the natural upgrade path for
the future polyphonic Piano/Full Song modes (section 37 of the spec).

pYIN is monophonic: it tracks ONE pitch at a time, which is exactly what
Melody mode needs (vocal line / lead instrument). It is not used, and must
not be used, for polyphonic modes — those are explicitly "Coming Soon".
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

import librosa
import numpy as np

logger = logging.getLogger("transcore.transcription")


@dataclass
class NoteEvent:
    pitch_midi: int
    start: float  # seconds
    end: float  # seconds
    velocity: int = 90


def basic_pitch_available() -> bool:
    try:
        import basic_pitch  # noqa: F401
        import tensorflow  # noqa: F401

        return True
    except Exception:
        return False


def _pyin_transcribe(
    y: np.ndarray,
    sr: int,
    fmin: str = "C2",
    fmax: str = "C7",
    min_note_duration: float = 0.08,
    voiced_prob_threshold: float = 0.5,
) -> List[NoteEvent]:
    f0, voiced_flag, voiced_prob = librosa.pyin(
        y,
        fmin=librosa.note_to_hz(fmin),
        fmax=librosa.note_to_hz(fmax),
        sr=sr,
        frame_length=2048,
    )
    times = librosa.times_like(f0, sr=sr)
    hop = times[1] - times[0] if len(times) > 1 else 0.01

    midi_seq = np.full_like(f0, fill_value=np.nan, dtype=float)
    valid = voiced_flag & (voiced_prob >= voiced_prob_threshold) & ~np.isnan(f0)
    midi_seq[valid] = librosa.hz_to_midi(f0[valid])
    midi_rounded = np.round(midi_seq)

    events: List[NoteEvent] = []
    current_pitch: Optional[int] = None
    seg_start: Optional[float] = None

    def flush(end_time: float):
        nonlocal current_pitch, seg_start
        if current_pitch is not None and seg_start is not None:
            if end_time - seg_start >= min_note_duration:
                events.append(
                    NoteEvent(pitch_midi=int(current_pitch), start=float(seg_start), end=float(end_time))
                )
        current_pitch = None
        seg_start = None

    for t, p in zip(times, midi_rounded):
        if np.isnan(p):
            flush(t)
            continue
        p_int = int(p)
        if current_pitch is None:
            current_pitch = p_int
            seg_start = t
        elif p_int != current_pitch:
            flush(t)
            current_pitch = p_int
            seg_start = t

    if current_pitch is not None and seg_start is not None:
        flush(times[-1] + hop if len(times) else seg_start + min_note_duration)

    return events


def transcribe_melody(filepath: str, engine: str = "pyin") -> List[NoteEvent]:
    """Transcribe the dominant monophonic melody line from an audio file.

    Raises RuntimeError (never returns fake notes) if the requested engine
    is unavailable or the audio yields no usable pitch content.
    """
    y, sr = librosa.load(filepath, sr=None, mono=True)
    if len(y) == 0:
        raise RuntimeError("Audio file contains no samples.")

    if engine == "basic_pitch":
        if not basic_pitch_available():
            raise RuntimeError(
                "engine=basic_pitch was requested but basic-pitch/tensorflow "
                "is not installed in this environment. Install it manually "
                "(see README) or use engine=pyin (default)."
            )
        return _basic_pitch_transcribe(filepath)

    events = _pyin_transcribe(y, sr)
    if not events:
        raise RuntimeError(
            "No clear monophonic pitch content was detected in this audio. "
            "This can happen with instrumental/dense mixes, silence, or "
            "very low-volume recordings — Melody mode works best on audio "
            "with a clear lead vocal or solo instrument line."
        )
    return events


def _basic_pitch_transcribe(filepath: str) -> List[NoteEvent]:  # pragma: no cover
    """Optional Basic Pitch (polyphonic-capable) path. Only reachable when
    basic-pitch + tensorflow are actually installed and importable.
    """
    from basic_pitch.inference import predict
    from basic_pitch import ICASSP_2022_MODEL_PATH

    model_output, midi_data, note_events = predict(filepath, ICASSP_2022_MODEL_PATH)
    events = []
    for start, end, pitch, amplitude, _pitch_bend in note_events:
        events.append(
            NoteEvent(
                pitch_midi=int(pitch),
                start=float(start),
                end=float(end),
                velocity=int(min(127, max(1, round(amplitude * 127)))),
            )
        )
    return events
