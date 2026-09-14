import { AudioWaveform } from "lucide-react";
import { UploadZone } from "../components/UploadZone";

export function LandingPage({ onFileSelected }: { onFileSelected: (file: File) => void }) {
  return (
    <div className="mx-auto max-w-3xl px-6 py-20 sm:py-28">
      <div className="mb-3 flex items-center gap-2 text-signal">
        <AudioWaveform className="h-5 w-5" strokeWidth={1.5} />
        <span className="text-sm tracking-wide">TRANSCORE AI</span>
      </div>

      <h1 className="font-display text-4xl leading-tight text-paper sm:text-6xl">
        Turn sound into notation.
      </h1>

      <p className="mt-6 max-w-xl text-lg text-paper-dim">
        Upload a song, choose how you want it transcribed, and let AI create your score —
        readable, editable, and ready for MuseScore.
      </p>

      <div className="mt-12">
        <UploadZone onFileSelected={onFileSelected} />
      </div>

      <p className="mt-6 text-xs text-paper-faint">
        Upload audio that you have the right to process. Your audio is processed locally and
        temporary processing files are automatically removed.
      </p>
    </div>
  );
}
