import { useCallback, useState } from "react";
import { AudioWaveform, AlertCircle } from "lucide-react";
import { StepIndicator, type StepName } from "./components/StepIndicator";
import { LandingPage } from "./pages/LandingPage";
import { AnalyzeChoosePage } from "./pages/AnalyzeChoosePage";
import { ProcessingPage } from "./pages/ProcessingPage";
import { ResultPage } from "./pages/ResultPage";
import {
  ApiError,
  getAnalysis,
  getJobResult,
  getJobStatus,
  pollUntil,
  startTranscription,
  uploadAudio,
} from "./services/api";
import type { AnalysisResponse, JobResultResponse, JobStatusResponse, TranscriptionMode } from "./types/api";

type Screen =
  | { name: "landing" }
  | { name: "uploading"; filename: string }
  | { name: "analyzed"; jobId: string; filename: string; analysis: AnalysisResponse }
  | { name: "starting"; jobId: string; filename: string; analysis: AnalysisResponse }
  | { name: "processing"; jobId: string; status: JobStatusResponse }
  | { name: "done"; result: JobResultResponse }
  | { name: "error"; message: string };

const SCREEN_TO_STEP: Record<Screen["name"], StepName> = {
  landing: "Upload",
  uploading: "Analyze",
  analyzed: "Choose",
  starting: "Choose",
  processing: "Transcribe",
  done: "Export",
  error: "Upload",
};

export default function App() {
  const [screen, setScreen] = useState<Screen>({ name: "landing" });

  const handleFileSelected = useCallback(async (file: File) => {
    setScreen({ name: "uploading", filename: file.name });
    try {
      const upload = await uploadAudio(file);
      const analysis = await pollUntil(
        () => getAnalysis(upload.job_id),
        (a) => a.status === "analyzed" || a.status === "failed"
      );
      if (analysis.status === "failed") {
        throw new Error("Audio analysis failed.");
      }
      setScreen({ name: "analyzed", jobId: upload.job_id, filename: file.name, analysis });
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Something went wrong during upload.";
      setScreen({ name: "error", message });
    }
  }, []);

  const handleTranscribe = useCallback(
    async (jobId: string, filename: string, analysis: AnalysisResponse, mode: TranscriptionMode) => {
      setScreen({ name: "starting", jobId, filename, analysis });
      try {
        await startTranscription(jobId, { mode });

        let finalStatus: JobStatusResponse = await getJobStatus(jobId);
        setScreen({ name: "processing", jobId, status: finalStatus });

        while (finalStatus.status !== "completed" && finalStatus.status !== "failed") {
          await new Promise((r) => setTimeout(r, 700));
          finalStatus = await getJobStatus(jobId);
          setScreen({ name: "processing", jobId, status: finalStatus });
        }

        if (finalStatus.status === "failed") {
          setScreen({ name: "error", message: finalStatus.error ?? "Transcription failed." });
          return;
        }

        const result = await getJobResult(jobId);
        setScreen({ name: "done", result });
      } catch (err) {
        const message = err instanceof ApiError ? err.message : "Something went wrong during transcription.";
        setScreen({ name: "error", message });
      }
    },
    []
  );

  return (
    <div className="min-h-screen">
      <header className="border-b border-ink-line">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2 text-paper">
            <AudioWaveform className="h-4 w-4 text-signal" strokeWidth={1.5} />
            <span className="font-display text-sm tracking-wide">TRANSCORE AI</span>
          </div>
          <StepIndicator current={SCREEN_TO_STEP[screen.name]} />
        </div>
      </header>

      <main>
        {screen.name === "landing" && <LandingPage onFileSelected={handleFileSelected} />}

        {screen.name === "uploading" && (
          <div className="mx-auto max-w-2xl px-6 py-24 text-center">
            <p className="font-display text-2xl text-paper">Analyzing {screen.filename}…</p>
            <p className="mt-2 text-sm text-paper-dim">
              Reading audio, detecting tempo, key and time signature.
            </p>
          </div>
        )}

        {(screen.name === "analyzed" || screen.name === "starting") && (
          <AnalyzeChoosePage
            analysis={screen.analysis}
            filename={screen.filename}
            isStarting={screen.name === "starting"}
            onTranscribe={(mode) => handleTranscribe(screen.jobId, screen.filename, screen.analysis, mode)}
          />
        )}

        {screen.name === "processing" && <ProcessingPage status={screen.status} />}

        {screen.name === "done" && (
          <ResultPage result={screen.result} onStartOver={() => setScreen({ name: "landing" })} />
        )}

        {screen.name === "error" && (
          <div className="mx-auto max-w-lg px-6 py-24 text-center">
            <AlertCircle className="mx-auto mb-4 h-8 w-8 text-flat" />
            <p className="font-display text-2xl text-paper">Something went wrong</p>
            <p className="mt-3 text-sm text-paper-dim">{screen.message}</p>
            <button
              type="button"
              onClick={() => setScreen({ name: "landing" })}
              className="mt-8 rounded-xl border border-ink-line px-6 py-3 text-sm text-paper hover:border-signal/50"
            >
              Start over
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
