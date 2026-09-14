"""
musicxml_generator.py — Builds a real, valid MusicXML score (via music21)
from cleaned note events. Output opens directly in MuseScore.
"""
from __future__ import annotations

from typing import List, Optional

from music21 import stream, note, tempo as m21tempo, meter, key as m21key, metadata, duration as m21duration

from app.services.transcription import NoteEvent

_KEY_TO_M21 = None  # populated lazily; music21 parses "C major" style strings directly


def build_melody_score(
    events: List[NoteEvent],
    tempo_bpm: Optional[float],
    key_label: Optional[str],
    time_signature: str,
    song_title: str = "Untitled Transcription",
) -> stream.Score:
    score = stream.Score()
    score.metadata = metadata.Metadata()
    score.metadata.title = song_title
    score.metadata.composer = "AI-generated transcription (TRANSCORE AI)"

    part = stream.Part()
    part.partName = "Melody"

    # Time signature (always present — required by spec section 13)
    try:
        ts = meter.TimeSignature(time_signature)
    except Exception:
        ts = meter.TimeSignature("4/4")
    part.insert(0, ts)

    # Tempo
    bpm = tempo_bpm or 120.0
    part.insert(0, m21tempo.MetronomeMark(number=round(bpm)))

    # Key signature — only added if we actually detected one (never fabricated)
    if key_label:
        try:
            tonic, mode = key_label.rsplit(" ", 1)
            part.insert(0, m21key.Key(tonic, mode.lower()))
        except Exception:
            pass

    if not events:
        # Still produce a valid, openable (empty) score rather than nothing.
        r = note.Rest()
        r.duration = m21duration.Duration(4.0)
        part.append(r)
        score.append(part)
        return score

    quarter_seconds = 60.0 / bpm

    cursor = 0.0
    sorted_events = sorted(events, key=lambda e: e.start)
    for e in sorted_events:
        start_ql = e.start / quarter_seconds
        end_ql = e.end / quarter_seconds
        length_ql = max(0.125, end_ql - start_ql)

        if start_ql - cursor > 0.05:
            r = note.Rest()
            r.duration = m21duration.Duration(round((start_ql - cursor) * 4) / 4 or 0.25)
            part.append(r)

        n = note.Note()
        n.pitch.midi = e.pitch_midi
        n.duration = m21duration.Duration(round(length_ql * 4) / 4 or 0.25)
        n.volume.velocity = e.velocity
        part.append(n)
        cursor = start_ql + n.duration.quarterLength

    part.makeMeasures(inPlace=True)
    score.append(part)
    return score


def export_musicxml(score: stream.Score, out_path: str) -> str:
    score.write("musicxml", fp=out_path)
    return out_path
