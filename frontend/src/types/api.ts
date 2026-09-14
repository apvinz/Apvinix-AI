export type JobStatus =
  | "pending"
  | "analyzing"
  | "analyzed"
  | "transcribing"
  | "cleaning_midi"
  | "building_score"
  | "completed"
  | "failed";

export type TranscriptionMode = "melody" | "melody_chords" | "piano" | "full_song";

export interface UploadResponse {
  job_id: string;
  filename: string;
  status: JobStatus;
}

export interface AnalysisResponse {
  job_id: string;
  status: JobStatus;
  duration_seconds: number;
  tempo_bpm: number | null;
  key: string | null;
  time_signature: string;
  time_signature_confidence: "detected" | "assumed" | null;
  is_silent: boolean;
  available_modes: TranscriptionMode[];
  coming_soon_modes: TranscriptionMode[];
}

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  progress: number;
  current_step: string;
  error?: string | null;
}

export interface JobResultResponse {
  job_id: string;
  status: JobStatus;
  song_title: string;
  duration_seconds: number;
  tempo_bpm: number | null;
  key: string | null;
  time_signature: string;
  note_count: number;
  musicxml_url: string;
  midi_url: string;
  engine_used: string;
}

export interface ApiErrorBody {
  detail: string;
}
