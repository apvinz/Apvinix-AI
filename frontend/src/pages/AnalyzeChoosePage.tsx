import { useState } from "react";
import { Sparkles } from "lucide-react";
import type { AnalysisResponse, TranscriptionMode } from "../types/api";
import { AnalysisPanel } from "../components/AnalysisPanel";
import { ModeSelector } from "../components/ModeSelector";

interface Props {
  analysis: AnalysisResponse;
  filename: string;
  onTranscribe: (mode: TranscriptionMode) => void;
  isStarting: boolean;
}

export function AnalyzeChoosePage({ analysis, filename, onTranscribe, isStarting }: Props) {
  const [selected, setSelected] = useState<TranscriptionMode>("melody");

  return (
    <div className="mx-auto max-w-3xl px-6 py-14">
      <p className="text-sm text-paper-faint">{filename}</p>
      <h2 className="mt-1 font-display text-3xl text-paper">What do you want to create?</h2>

      <div className="mt-8">
        <AnalysisPanel analysis={analysis} />
      </div>

      {analysis.available_modes.includes("full_song") === false &&
        analysis.available_modes.length === 1 && (
          <div className="mt-6 flex items-start gap-2 rounded-lg border border-signal/30 bg-signal/5 px-4 py-3 text-sm text-paper-dim">
            <Sparkles className="mt-0.5 h-4 w-4 flex-shrink-0 text-signal" />
            <span>
              This build ships with <strong className="text-paper">Melody</strong> transcription fully
              working. Melody + Chords, Piano and Full Song are on the roadmap — see section 37 of the
              product spec — and are shown as Coming Soon rather than faked.
            </span>
          </div>
        )}

      <div className="mt-8">
        <ModeSelector
          availableModes={analysis.available_modes}
          selected={selected}
          onSelect={setSelected}
        />
      </div>

      <button
        type="button"
        disabled={isStarting}
        onClick={() => onTranscribe(selected)}
        className="mt-10 w-full rounded-xl bg-signal py-3.5 font-medium text-ink transition-opacity hover:opacity-90 disabled:opacity-50 sm:w-auto sm:px-10"
      >
        {isStarting ? "Starting…" : "Transcribe selected"}
      </button>
    </div>
  );
}
