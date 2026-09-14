import type { JobStatusResponse } from "../types/api";
import { ProcessingView } from "../components/ProcessingView";

export function ProcessingPage({ status }: { status: JobStatusResponse }) {
  return (
    <div className="mx-auto max-w-2xl px-6 py-20">
      <h2 className="mb-8 font-display text-3xl text-paper">Transcribing your song</h2>
      <ProcessingView status={status} />
      {status.status === "failed" && (
        <div className="mt-6 rounded-lg border border-flat/30 bg-flat/10 px-4 py-3 text-sm text-flat">
          {status.error ?? "Transcription failed."}
        </div>
      )}
    </div>
  );
}
