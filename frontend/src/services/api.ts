import type {
  AnalysisResponse,
  ApiErrorBody,
  JobResultResponse,
  JobStatusResponse,
  TranscriptionMode,
  UploadResponse,
} from "../types/api";

// Base URL for the backend API.
// - Local dev: leave VITE_API_BASE_URL unset, Vite's dev proxy (vite.config.ts)
//   forwards "/api" to http://127.0.0.1:8000 automatically.
// - Production (Netlify): set VITE_API_BASE_URL in Netlify's environment
//   variables to your deployed backend URL, e.g.
//   https://your-backend.onrender.com/api
const BASE = import.meta.env.VITE_API_BASE_URL || "/api";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as ApiErrorBody;
      if (body?.detail) detail = body.detail;
    } catch {
      /* ignore — no JSON body */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export async function uploadAudio(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/upload`, { method: "POST", body: form });
  return handle<UploadResponse>(res);
}

export async function getAnalysis(jobId: string): Promise<AnalysisResponse> {
  const res = await fetch(`${BASE}/jobs/${jobId}/analysis`);
  return handle<AnalysisResponse>(res);
}

export interface TranscribeOptions {
  mode: TranscriptionMode;
  quantization?: "auto" | "1/4" | "1/8" | "1/16" | "1/32";
  remove_duplicate_notes?: boolean;
  remove_short_noise?: boolean;
  engine?: "pyin" | "basic_pitch";
}

export async function startTranscription(
  jobId: string,
  options: TranscribeOptions
): Promise<JobStatusResponse> {
  const res = await fetch(`${BASE}/transcribe/${jobId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(options),
  });
  return handle<JobStatusResponse>(res);
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const res = await fetch(`${BASE}/jobs/${jobId}`);
  return handle<JobStatusResponse>(res);
}

export async function getJobResult(jobId: string): Promise<JobResultResponse> {
  const res = await fetch(`${BASE}/jobs/${jobId}/result`);
  return handle<JobResultResponse>(res);
}

export function musicxmlDownloadUrl(jobId: string): string {
  return `${BASE}/jobs/${jobId}/musicxml`;
}

export function midiDownloadUrl(jobId: string): string {
  return `${BASE}/jobs/${jobId}/midi`;
}

/** Polls a job until it reaches one of the target statuses or times out. */
export async function pollUntil<T>(
  fn: () => Promise<T>,
  isDone: (result: T) => boolean,
  { intervalMs = 800, timeoutMs = 5 * 60 * 1000 } = {}
): Promise<T> {
  const start = Date.now();
  // First attempt immediately, then on an interval.
  // Swallows transient 202s by letting the caller's isDone/try handle it.
  for (;;) {
    try {
      const result = await fn();
      if (isDone(result)) return result;
    } catch (err) {
      if (err instanceof ApiError && err.status !== 202) {
        throw err;
      }
      // 202/transient -> keep polling
    }
    if (Date.now() - start > timeoutMs) {
      throw new Error("Timed out waiting for the job to complete.");
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}
