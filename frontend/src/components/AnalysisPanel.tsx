import type { AnalysisResponse } from "../types/api";

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function Stat({ label, value, muted }: { label: string; value: string; muted?: boolean }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs text-paper-faint">{label}</span>
      <span className={["font-display text-2xl", muted ? "text-paper-dim" : "text-paper"].join(" ")}>
        {value}
      </span>
    </div>
  );
}

export function AnalysisPanel({ analysis }: { analysis: AnalysisResponse }) {
  return (
    <div className="rounded-2xl border border-ink-line bg-ink-card p-6">
      <h3 className="mb-5 font-display text-lg text-paper">Song analysis</h3>
      <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
        <Stat label="Duration" value={formatDuration(analysis.duration_seconds)} />
        <Stat
          label="Tempo"
          value={analysis.tempo_bpm ? `${analysis.tempo_bpm} BPM` : "Unknown"}
          muted={!analysis.tempo_bpm}
        />
        <Stat label="Key" value={analysis.key ?? "Unknown"} muted={!analysis.key} />
        <Stat
          label="Time signature"
          value={analysis.time_signature}
          muted={analysis.time_signature_confidence !== "detected"}
        />
      </div>

      {analysis.time_signature_confidence === "assumed" && (
        <p className="mt-4 text-xs text-paper-faint">
          Time signature could not be reliably detected — showing the common default (4/4). You can change
          this in Score Settings.
        </p>
      )}

      {analysis.is_silent && (
        <p className="mt-4 rounded-lg border border-flat/30 bg-flat/10 px-3 py-2 text-sm text-flat">
          This audio appears to be silent or near-silent. Transcription may not find any notes.
        </p>
      )}
    </div>
  );
}
