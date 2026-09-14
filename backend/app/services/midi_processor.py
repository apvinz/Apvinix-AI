"""
midi_processor.py — Turns raw note events into a cleaned, quantized,
MIDI-file-backed note list ready for score arrangement.

Pipeline (matches spec section 12):
  raw note events
    -> remove duplicate/overlapping notes
    -> remove very short noise notes
    -> quantize timing to a musical grid
    -> write real .mid file via mido
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import mido

from app.services.transcription import NoteEvent

QUANTIZE_GRID = {
    "1/4": 4,
    "1/8": 8,
    "1/16": 16,
    "1/32": 32,
}


@dataclass
class CleanupOptions:
    remove_duplicates: bool = True
    remove_short_noise: bool = True
    min_note_seconds: float = 0.09
    quantize: str = "auto"  # "auto" | "1/4" | "1/8" | "1/16" | "1/32"


def _remove_duplicates(events: List[NoteEvent]) -> List[NoteEvent]:
    events = sorted(events, key=lambda e: e.start)
    cleaned: List[NoteEvent] = []
    for e in events:
        if cleaned and cleaned[-1].pitch_midi == e.pitch_midi and e.start < cleaned[-1].end + 0.02:
            # merge into previous note instead of duplicating it
            cleaned[-1] = NoteEvent(
                pitch_midi=cleaned[-1].pitch_midi,
                start=cleaned[-1].start,
                end=max(cleaned[-1].end, e.end),
                velocity=cleaned[-1].velocity,
            )
        else:
            cleaned.append(e)
    return cleaned


def _remove_short_noise(events: List[NoteEvent], min_seconds: float) -> List[NoteEvent]:
    return [e for e in events if (e.end - e.start) >= min_seconds]


def _choose_auto_grid(events: List[NoteEvent], tempo_bpm: Optional[float]) -> str:
    """Pick a sensible quantization grid from the shortest recurring note
    duration, rather than guessing blindly."""
    if not events:
        return "1/8"
    durations = sorted(e.end - e.start for e in events)
    median = durations[len(durations) // 2]
    beat_seconds = 60.0 / tempo_bpm if tempo_bpm else 0.5
    ratio = median / beat_seconds if beat_seconds else 0.5
    if ratio >= 0.85:
        return "1/4"
    if ratio >= 0.4:
        return "1/8"
    if ratio >= 0.2:
        return "1/16"
    return "1/32"


def quantize_events(events: List[NoteEvent], tempo_bpm: Optional[float], grid: str) -> List[NoteEvent]:
    if grid == "auto":
        grid = _choose_auto_grid(events, tempo_bpm)
    division = QUANTIZE_GRID.get(grid, 8)
    beat_seconds = 60.0 / tempo_bpm if tempo_bpm else 0.5
    step = beat_seconds * (4.0 / division) / 4.0  # seconds per grid unit (in quarter-note terms)
    # step above simplifies to: seconds per (1/division) note
    step = (beat_seconds * 4.0) / division

    def snap(t: float) -> float:
        return round(t / step) * step if step > 0 else t

    quantized = []
    for e in events:
        start_q = snap(e.start)
        end_q = snap(e.end)
        if end_q <= start_q:
            end_q = start_q + step
        quantized.append(NoteEvent(pitch_midi=e.pitch_midi, start=start_q, end=end_q, velocity=e.velocity))
    return quantized


def clean_note_events(
    events: List[NoteEvent], tempo_bpm: Optional[float], options: Optional[CleanupOptions] = None
) -> List[NoteEvent]:
    options = options or CleanupOptions()
    result = events
    if options.remove_duplicates:
        result = _remove_duplicates(result)
    if options.remove_short_noise:
        result = _remove_short_noise(result, options.min_note_seconds)
    result = quantize_events(result, tempo_bpm, options.quantize)
    return sorted(result, key=lambda e: e.start)


def write_midi_file(events: List[NoteEvent], tempo_bpm: Optional[float], out_path: str) -> str:
    """Writes a genuine standard MIDI file (type 0) from cleaned note events."""
    mid = mido.MidiFile(type=0)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    bpm = tempo_bpm or 120.0
    track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0))
    track.append(mido.Message("program_change", program=0, time=0))

    ticks_per_beat = mid.ticks_per_beat
    seconds_per_tick = (60.0 / bpm) / ticks_per_beat

    def sec_to_ticks(s: float) -> int:
        return max(0, round(s / seconds_per_tick))

    midi_events = []
    for e in events:
        midi_events.append((sec_to_ticks(e.start), "on", e.pitch_midi, e.velocity))
        midi_events.append((sec_to_ticks(e.end), "off", e.pitch_midi, 0))
    midi_events.sort(key=lambda x: (x[0], 0 if x[1] == "off" else 1))

    last_tick = 0
    for tick, kind, pitch, vel in midi_events:
        delta = max(0, tick - last_tick)
        if kind == "on":
            track.append(mido.Message("note_on", note=pitch, velocity=vel, time=delta))
        else:
            track.append(mido.Message("note_off", note=pitch, velocity=0, time=delta))
        last_tick = tick

    mid.save(out_path)
    return out_path
