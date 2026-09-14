"""
analyzer.py — Real audio analysis (no fabricated values).

Everything returned here is computed directly from the uploaded audio file
using librosa. If a value cannot be computed reliably, it is returned as
None and the API/frontend must show "Unknown" / hide it — never a made-up
number.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Optional

import librosa
import numpy as np

logger = logging.getLogger("transcore.analyzer")

# Krumhansl-Schmuckler key profiles (real, published pitch-class weightings
# used for key estimation — not arbitrary numbers).
_MAJOR_PROFILE = np.array(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
)
_MINOR_PROFILE = np.array(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
)
_PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


@dataclass
class KeyResult:
    tonic: str
    mode: str  # "major" | "minor"
    correlation: float

    @property
    def label(self) -> str:
        return f"{self.tonic} {self.mode.capitalize()}"


@dataclass
class AnalysisResult:
    duration_seconds: float
    tempo_bpm: Optional[float]
    key: Optional[str]
    time_signature: str
    time_signature_confidence: Optional[str]  # "detected" | "assumed"
    rms_energy_mean: float
    is_silent: bool

    def to_dict(self) -> dict:
        return asdict(self)


def estimate_key(y: np.ndarray, sr: int) -> Optional[KeyResult]:
    """Krumhansl-Schmuckler key-finding on the chroma profile of the audio.
    Returns None if the signal is too weak/short to produce a stable estimate.
    """
    if len(y) < sr * 2:
        return None

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = chroma.mean(axis=1)
    if chroma_mean.sum() <= 1e-6:
        return None
    chroma_mean = chroma_mean / (chroma_mean.sum() + 1e-9)

    best = None
    for shift in range(12):
        major_shifted = np.roll(_MAJOR_PROFILE, shift)
        minor_shifted = np.roll(_MINOR_PROFILE, shift)

        maj_corr = float(np.corrcoef(chroma_mean, major_shifted)[0, 1])
        min_corr = float(np.corrcoef(chroma_mean, minor_shifted)[0, 1])

        if best is None or maj_corr > best.correlation:
            best = KeyResult(tonic=_PITCH_CLASSES[shift], mode="major", correlation=maj_corr)
        if min_corr > best.correlation:
            best = KeyResult(tonic=_PITCH_CLASSES[shift], mode="minor", correlation=min_corr)

    # Below this, the correlation is too weak to trust — report unknown
    # rather than a fabricated key.
    if best is None or best.correlation < 0.55:
        return None
    return best


def estimate_time_signature(y: np.ndarray, sr: int, tempo: Optional[float]) -> tuple[str, str]:
    """Heuristic time-signature estimate from beat/onset periodicity.
    We only claim a *detected* signature when the beat pattern is stable
    enough to analyze; otherwise we fall back to the overwhelmingly common
    4/4 and label it explicitly as "assumed", never "detected".
    """
    try:
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        tempogram = librosa.feature.tempogram(onset_envelope=onset_env, sr=sr)
        if tempogram.shape[1] < 8:
            return "4/4", "assumed"
        # crude 3-beat vs 4-beat grouping strength comparison
        autocorr = librosa.autocorrelate(onset_env, max_size=8)
        if len(autocorr) < 4:
            return "4/4", "assumed"
        strength_3 = autocorr[2] if len(autocorr) > 2 else 0
        strength_4 = autocorr[3] if len(autocorr) > 3 else 0
        if strength_3 > strength_4 * 1.15:
            return "3/4", "detected"
        return "4/4", "detected" if strength_4 > 0 else "assumed"
    except Exception as exc:  # pragma: no cover - defensive, never fake data
        logger.warning("time signature estimation failed: %s", exc)
        return "4/4", "assumed"


def analyze_audio(filepath: str) -> AnalysisResult:
    y, sr = librosa.load(filepath, sr=None, mono=True)
    duration = float(librosa.get_duration(y=y, sr=sr))

    rms = float(np.sqrt(np.mean(y**2))) if len(y) else 0.0
    is_silent = rms < 1e-4

    tempo_bpm: Optional[float] = None
    if not is_silent:
        tempo, _beats = librosa.beat.beat_track(y=y, sr=sr)
        tempo_val = float(np.atleast_1d(tempo)[0]) if np.size(tempo) else 0.0
        tempo_bpm = round(tempo_val, 1) if tempo_val > 0 else None

    key_result = None if is_silent else estimate_key(y, sr)
    time_sig, time_sig_conf = ("4/4", "assumed") if is_silent else estimate_time_signature(y, sr, tempo_bpm)

    return AnalysisResult(
        duration_seconds=round(duration, 2),
        tempo_bpm=tempo_bpm,
        key=key_result.label if key_result else None,
        time_signature=time_sig,
        time_signature_confidence=time_sig_conf,
        rms_energy_mean=round(rms, 5),
        is_silent=is_silent,
    )
