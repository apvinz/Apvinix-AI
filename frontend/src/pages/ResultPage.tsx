import { Download, FileMusic, RefreshCcw } from "lucide-react";
import type { JobResultResponse } from "../types/api";
import { ScorePreview } from "../components/ScorePreview";
import { midiDownloadUrl, musicxmlDownloadUrl } from "../services/api";

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

interface Props {
  result: JobResultResponse;
  onStartOver: () => void;
}

export function ResultPage({ result, onStartOver }: Props) {
  return (
    <div className="mx-auto max-w-4xl px-6 py-14">
      <div className="mb-2 flex items-center gap-2 text-tuned">
        <FileMusic className="h-4 w-4" />
        <span className="text-sm tracking-wide">Transcription complete</span>
      </div>
      <h2 className="font-display text-3xl text-paper">{result.song_title}</h2>

      <div className="mt-4 flex flex-wrap gap-x-8 gap-y-2 text-sm text-paper-dim">
        <span>{formatDuration(result.duration_seconds)}</span>
        {result.tempo_bpm && <span>{result.tempo_bpm} BPM</span>}
        {result.key && <span>{result.key}</span>}
        <span>{result.time_signature}</span>
        <span>{result.note_count} notes</span>
      </div>

      <div className="mt-8">
        <ScorePreview musicxmlUrl={musicxmlDownloadUrl(result.job_id)} />
      </div>

      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        <a
          href={musicxmlDownloadUrl(result.job_id)}
          download
          className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-signal py-3.5 font-medium text-ink transition-opacity hover:opacity-90"
        >
          <Download className="h-4 w-4" />
          Download MusicXML
        </a>
        <a
          href={midiDownloadUrl(result.job_id)}
          download
          className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-ink-line py-3.5 font-medium text-paper transition-colors hover:border-signal/50"
        >
          <Download className="h-4 w-4" />
          Download MIDI
        </a>
      </div>

      <p className="mt-4 text-xs text-paper-faint">
        Open the MusicXML file in MuseScore to view, edit, and play your score. AI-generated
        transcription designed to preserve the musical structure and performance as accurately as
        possible — not a guarantee of an identical match to the original recording.
      </p>

      <button
        type="button"
        onClick={onStartOver}
        className="mt-10 flex items-center gap-2 text-sm text-paper-dim hover:text-paper"
      >
        <RefreshCcw className="h-3.5 w-3.5" />
        Transcribe another song
      </button>
    </div>
  );
}
