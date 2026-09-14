"""
TRANSCORE AI — environment checker.

Run this after setting up your virtualenv to confirm everything the
backend actually needs is installed and working. Every check here really
imports/executes the thing it claims to check — there is no "assume it's
fine" step.

    .venv\\Scripts\\activate
    python check_environment.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, fn):
    try:
        detail = fn()
        RESULTS.append((name, True, detail or "OK"))
    except Exception as exc:
        RESULTS.append((name, False, str(exc)))


def check_python():
    v = sys.version_info
    if v < (3, 9):
        raise RuntimeError(f"Python {v.major}.{v.minor} is too old. Need 3.9+")
    return f"Python {v.major}.{v.minor}.{v.micro}"


def check_ffmpeg():
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError("FFmpeg was not found. Please install FFmpeg and add it to PATH.")
    proc = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=10)
    first_line = proc.stdout.splitlines()[0] if proc.stdout else "unknown version"
    return first_line


def check_ffprobe():
    path = shutil.which("ffprobe")
    if not path:
        raise RuntimeError("ffprobe was not found (ships with FFmpeg). Check your FFmpeg install.")
    return path


def check_numpy():
    import numpy
    return f"numpy {numpy.__version__}"


def check_scipy():
    import scipy
    return f"scipy {scipy.__version__}"


def check_librosa():
    import librosa
    # exercise the actual pYIN function, not just the import
    import numpy as np
    y = np.zeros(4096, dtype=float)
    librosa.pyin(y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"), sr=22050)
    return f"librosa {librosa.__version__} (pYIN verified callable)"

def check_music21():
    import music21
    # exercise real note/stream creation
    from music21 import note, stream
    s = stream.Stream()
    s.append(note.Note("C4"))
    return f"music21 {music21.__version__} (Stream/Note creation verified)"


def check_mido():
    import mido
    mid = mido.MidiFile()
    mid.tracks.append(mido.MidiTrack())
    return "mido (MIDI file creation verified)"


def check_fastapi():
    import fastapi
    return f"fastapi {fastapi.__version__}"


def check_basic_pitch_optional():
    try:
        import basic_pitch  # noqa: F401
        import tensorflow  # noqa: F401
        return "available (optional polyphonic engine enabled)"
    except Exception:
        return "not installed (optional — Melody mode does not need this)"


def main():
    check("Python version", check_python)
    check("FFmpeg", check_ffmpeg)
    check("ffprobe", check_ffprobe)
    check("NumPy", check_numpy)
    check("SciPy", check_scipy)
    check("librosa (pYIN engine)", check_librosa)
    check("music21", check_music21)
    check("mido", check_mido)
    check("FastAPI", check_fastapi)

    print("=" * 52)
    print("TRANSCORE AI ENVIRONMENT CHECK")
    print("=" * 52)

    required_ok = True
    for name, ok, detail in RESULTS:
        mark = "✓" if ok else "✗"
        print(f"{mark}  {name:<28} {detail}")
        if not ok:
            required_ok = False

    # Optional check, printed separately, never blocks readiness
    bp_detail = check_basic_pitch_optional()
    print(f"○  {'Basic Pitch (optional)':<28} {bp_detail}")

    print("=" * 52)
    if required_ok:
        print("Environment ready.")
        sys.exit(0)
    else:
        print("Environment NOT ready — fix the ✗ items above before running the server.")
        sys.exit(1)


if __name__ == "__main__":
    main()
