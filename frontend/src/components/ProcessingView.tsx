import { Check, Loader2 } from "lucide-react";
import type { JobStatusResponse } from "../types/api";

const PIPELINE_STEPS: { key: string; label: string }[] = [
  { key: "uploaded", label: "Audio uploaded" },
  { key: "preprocessing", label: "Audio preprocessed" },
  { key: "analyzing", label: "Tempo & key detected" },
  { key: "transcribing", label: "Transcribing notes" },
  { key: "cleaning_midi", label: "Cleaning MIDI" },
  { key: "building_score", label: "Building score" },
  { key: "exporting", label: "Generating MusicXML" },
  { key: "completed", label: "Score ready" },
];

export function ProcessingView({ status }: { status: JobStatusResponse }) {
  const currentIndex = PIPELINE_STEPS.findIndex((s) => s.key === status.current_step);

  return (
    <div className="rounded-2xl border border-ink-line bg-ink-card p-6">
      <div className="mb-6 flex items-center justify-between">
        <h3 className="font-display text-lg text-paper">TRANSCORE AI is working</h3>
        <span className="font-mono text-sm text-signal">{status.progress}%</span>
      </div>

      <div className="mb-6 h-1.5 w-full overflow-hidden rounded-full bg-ink-raised">
        <div
          className="h-full rounded-full bg-signal transition-all duration-500 ease-out"
          style={{ width: `${status.progress}%` }}
        />
      </div>

      <ul className="space-y-3">
        {PIPELINE_STEPS.map((step, i) => {
          const done = currentIndex > i || status.status === "completed";
          const active = i === currentIndex && status.status !== "completed";
          return (
            <li key={step.key} className="flex items-center gap-3 text-sm">
              {done ? (
                <Check className="h-4 w-4 flex-shrink-0 text-tuned" />
              ) : active ? (
                <Loader2 className="h-4 w-4 flex-shrink-0 animate-spin text-signal" />
              ) : (
                <span className="h-4 w-4 flex-shrink-0 rounded-full border border-ink-line" />
              )}
              <span className={done || active ? "text-paper" : "text-paper-faint"}>{step.label}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
