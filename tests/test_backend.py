"""
TRANSCORE AI backend tests.

Run with:
    cd backend
    .venv\\Scripts\\activate
    pip install pytest
    pytest ..\\tests -v

These tests exercise the real pipeline (no mocks) against a synthetic
audio file generated at test time — they will fail loudly if the audio
pipeline, MIDI generation, or MusicXML generation actually breaks.
"""
import io
import os
import sys
import time
import wave
import struct
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def make_test_wav(path: str, freq: float = 440.0, duration: float = 2.0, sr: int = 22050):
    import numpy as np
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    audio = 0.5 * np.sin(2 * np.pi * freq * t) * np.hanning(len(t))
    pcm = (audio * 32767).astype("int16")
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return path


@pytest.fixture
def test_audio(tmp_path):
    path = str(tmp_path / "test_tone.wav")
    return make_test_wav(path)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_upload_valid_audio(test_audio):
    with open(test_audio, "rb") as f:
        r = client.post("/api/upload", files={"file": ("test_tone.wav", f, "audio/wav")})
    assert r.status_code == 200
    body = r.json()
    assert "job_id" in body
    assert body["filename"] == "test_tone.wav"


def test_upload_rejects_wrong_extension():
    r = client.post("/api/upload", files={"file": ("not_audio.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def test_upload_rejects_empty_file():
    r = client.post("/api/upload", files={"file": ("empty.wav", b"", "audio/wav")})
    assert r.status_code == 400


def test_upload_rejects_corrupted_audio():
    # Valid extension, garbage bytes inside -> ffprobe must reject it
    r = client.post("/api/upload", files={"file": ("fake.wav", b"not a real wav file" * 20, "audio/wav")})
    assert r.status_code == 400


def _wait_for_status(job_id, target_statuses, timeout=30):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        r = client.get(f"/api/jobs/{job_id}")
        last = r.json()
        if last["status"] in target_statuses:
            return last
        time.sleep(0.2)
    raise TimeoutError(f"Job {job_id} did not reach {target_statuses} in time: {last}")


def test_full_melody_pipeline_end_to_end(test_audio):
    with open(test_audio, "rb") as f:
        r = client.post("/api/upload", files={"file": ("test_tone.wav", f, "audio/wav")})
    job_id = r.json()["job_id"]

    # wait for analysis
    deadline = time.time() + 20
    analysis = None
    while time.time() < deadline:
        r = client.get(f"/api/jobs/{job_id}/analysis")
        if r.status_code == 200:
            analysis = r.json()
            break
        time.sleep(0.2)
    assert analysis is not None, "Analysis never completed"
    assert analysis["duration_seconds"] > 0
    assert "melody" in analysis["available_modes"]

    r = client.post(f"/api/transcribe/{job_id}", json={"mode": "melody"})
    assert r.status_code == 200

    status = _wait_for_status(job_id, ("completed", "failed"), timeout=30)
    assert status["status"] == "completed", status

    r = client.get(f"/api/jobs/{job_id}/result")
    assert r.status_code == 200
    result = r.json()
    assert result["note_count"] > 0
    assert result["musicxml_url"]
    assert result["midi_url"]

    r = client.get(f"/api/jobs/{job_id}/musicxml")
    assert r.status_code == 200
    assert len(r.content) > 0
    assert b"score-partwise" in r.content or b"score-timewise" in r.content

    r = client.get(f"/api/jobs/{job_id}/midi")
    assert r.status_code == 200
    assert r.content[:4] == b"MThd"  # real standard MIDI file header


def test_coming_soon_modes_are_honestly_rejected(test_audio):
    with open(test_audio, "rb") as f:
        r = client.post("/api/upload", files={"file": ("test_tone.wav", f, "audio/wav")})
    job_id = r.json()["job_id"]
    _wait_for_status(job_id, ("analyzed", "failed"), timeout=20)

    for mode in ("piano", "melody_chords", "full_song"):
        r = client.post(f"/api/transcribe/{job_id}", json={"mode": mode})
        assert r.status_code == 501
        assert "Coming Soon" in r.json()["detail"]


def test_unknown_job_returns_404():
    r = client.get("/api/jobs/does-not-exist")
    assert r.status_code == 404
