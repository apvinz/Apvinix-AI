# TRANSCORE AI

**Turn sound into notation.**

Upload a song, choose how you want it transcribed, and let AI create a real,
editable score — exportable as MusicXML and MIDI, and compatible with
MuseScore.

---

## What actually works in this build (MVP)

This is a real, running application, not a mockup. Verified end-to-end:

```
Upload → Analyze (tempo/key/duration) → Melody transcription → MIDI →
MusicXML → Download → Open in MuseScore
```

| Feature | Status |
|---|---|
| Upload MP3/WAV/M4A/FLAC/OGG with real validation | ✅ Working |
| Audio analysis (duration, tempo, key, time signature) | ✅ Working (real detection, never fabricated) |
| **Melody transcription** (vocal / lead line) | ✅ Working |
| MIDI generation + cleanup (dedup, noise removal, quantization) | ✅ Working |
| MusicXML generation (opens in MuseScore) | ✅ Working |
| Score preview in-browser | ✅ Working (OpenSheetMusicDisplay) |
| Job-based async processing with real progress | ✅ Working |
| Melody + Chords | 🚧 Coming Soon (UI present, backend not implemented) |
| Piano arrangement | 🚧 Coming Soon |
| Full Song / stem separation | 🚧 Coming Soon |

Nothing above is faked. If a mode isn't implemented, the UI says **Coming
Soon** and the API returns `501` — it does not pretend to produce a result.

### Why librosa pYIN instead of Spotify's Basic Pitch?

The original brief suggested Basic Pitch as the transcription engine.
During implementation, Basic Pitch's TensorFlow dependency (`tensorflow<2.15.1`)
turned out to have **no working install path on Python 3.11/3.12**, and even
on the one Python version it does support (3.10) it's a heavy, fragile
dependency on Windows. That failed the brief's own requirement to pick
"the most stable, open-source, easy-to-run-on-Windows, easy-to-extend"
solution.

Instead, the default engine is **librosa's pYIN** (Mauch & Dixon, 2014) — a
real, peer-reviewed monophonic pitch-tracking algorithm that ships inside
`librosa` with zero native/GPU dependencies and installs identically on
Python 3.9 through 3.12. It's genuinely well-suited to Melody mode, since
that mode is monophonic by definition (one lead line).

Basic Pitch is still wired in as an **optional** secondary engine
(`engine: "basic_pitch"` in the transcribe request) for anyone who sets up a
Python 3.10 environment with it installed — see `backend/requirements.txt`.
It's the natural upgrade path toward the future polyphonic Piano/Full Song
modes.

---

## Project structure

```
transcore-ai/
├── frontend/          React + TypeScript + Vite + Tailwind
├── backend/           Python + FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── api/routes.py
│   │   ├── services/          audio_processor, analyzer, transcription,
│   │   │                      midi_processor, musicxml_generator, job_manager
│   │   └── schemas/job.py
│   ├── data/                  uploads/processing/outputs (gitignored)
│   ├── requirements.txt
│   └── check_environment.py
├── tests/              backend pytest suite (runs against the real pipeline)
└── .env.example
```

---

## Windows setup (from zero)

You'll need: **Python 3.10, 3.11 or 3.12**, **Node.js 18+**, **FFmpeg**, and
VS Code / PowerShell.

### 1. Install FFmpeg

Download a Windows build from https://www.gyan.dev/ffmpeg/builds/ (the
"essentials" build is enough), extract it, and add its `bin` folder to your
PATH. Confirm it worked:

```powershell
ffmpeg -version
```

### 2. Backend setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python check_environment.py
```

`check_environment.py` actually imports and exercises every dependency
(not just checks it's installed) and will tell you exactly what's missing
if something's wrong.

Run the backend:

```powershell
uvicorn app.main:app --reload
```

The API is now live at `http://127.0.0.1:8000`. Interactive docs at
`http://127.0.0.1:8000/docs`.

### 3. Frontend setup

Open a **second** PowerShell window (leave the backend running in the first):

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser. The dev server proxies
`/api/*` requests to the backend automatically (see `vite.config.ts`).

### 4. Run both together

You need both terminals running at once:
- Terminal 1: `backend\.venv\Scripts\activate` → `uvicorn app.main:app --reload`
- Terminal 2: `cd frontend` → `npm run dev`

---

## Using it

1. Drop an MP3/WAV/M4A/FLAC/OGG file on the landing page.
2. Wait for real analysis (duration, tempo, key, time signature).
3. Choose **Melody** (the only mode currently implemented — others show as
   Coming Soon).
4. Watch real, step-based progress (not a fake progress bar).
5. Preview the generated score in the browser.
6. Download the `.musicxml` and open it in MuseScore, or download the
   `.mid` file.

MuseScore is a free, separate desktop application — download it from
https://musescore.org if you don't already have it. This app does not (and
cannot) launch a desktop application directly from the browser; download,
then open the file in MuseScore yourself.

---

## Testing

**Backend** (exercises the real audio → MIDI → MusicXML pipeline against a
synthetically generated test tone — no mocks):

```powershell
cd backend
.venv\Scripts\activate
pip install pytest
pytest ..\tests -v
```

**Frontend:**

```powershell
cd frontend
npm run typecheck
npm run test
npm run build
```

---

## Privacy & copyright

Your audio is processed entirely on your own machine. Temporary
preprocessing files (normalized WAV copies) are stored under
`backend/data/processing/` and can be deleted via
`DELETE /api/jobs/{job_id}`; nothing is uploaded to any external service.

Only upload audio you have the right to process. This app does not include
— and will never include — a YouTube/Spotify downloader or any way to
fetch copyrighted audio you don't already have.

---

## Accuracy expectations

Audio → sheet music is not a lossless, perfect process. Recordings contain
mixing, reverb, expressive timing, and layered instruments that don't map
1:1 onto notation. This is an **AI-generated transcription designed to
preserve the musical structure and performance as accurately as possible**
— not a guarantee of an identical match to the original recording.

---

## Extending this (roadmap)

The architecture is deliberately set up so the next phases are additive,
not a rewrite:

- **Melody + Chords**: add a chord-estimation step (e.g. chroma-based
  template matching) in a new `services/chord_estimator.py`, feed its
  output into `musicxml_generator.py` as `ChordSymbol` objects above the
  existing melody staff.
- **Piano**: once a harmony/bass estimate exists, arrange into a
  `PartStaff` grand-staff pair (treble + bass clef) in
  `musicxml_generator.py`.
- **Full Song**: requires source separation (e.g. Demucs) as a new
  `services/stem_separator.py`, running `transcribe_melody`-style logic
  per stem, then merging into a multi-part `Score`.
- **Basic Pitch as polyphonic engine**: `transcription.py` already has a
  `_basic_pitch_transcribe()` path ready to activate once a compatible
  Python 3.10 environment is available.

Each of these should ship behind the existing `IMPLEMENTED_MODES` gate in
`app/schemas/job.py` — flip a mode from Coming Soon to available only once
it's genuinely producing real output end-to-end.
