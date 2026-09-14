import { useCallback, useRef, useState } from "react";
import { UploadCloud, AlertCircle } from "lucide-react";

const ACCEPTED_EXT = [".mp3", ".wav", ".m4a", ".flac", ".ogg"];
const MAX_SIZE_MB = 100;

interface Props {
  onFileSelected: (file: File) => void;
  disabled?: boolean;
}

function validateClientSide(file: File): string | null {
  const ext = "." + file.name.split(".").pop()?.toLowerCase();
  if (!ACCEPTED_EXT.includes(ext)) {
    return `Unsupported file type "${ext}". Use ${ACCEPTED_EXT.join(", ")}.`;
  }
  if (file.size === 0) {
    return "This file is empty.";
  }
  if (file.size > MAX_SIZE_MB * 1024 * 1024) {
    return `File is larger than ${MAX_SIZE_MB} MB.`;
  }
  return null;
}

export function UploadZone({ onFileSelected, disabled }: Props) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    (file: File) => {
      const validationError = validateClientSide(file);
      if (validationError) {
        setError(validationError);
        return;
      }
      setError(null);
      onFileSelected(file);
    },
    [onFileSelected]
  );

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(e) => {
          if (!disabled && (e.key === "Enter" || e.key === " ")) inputRef.current?.click();
        }}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          if (disabled) return;
          const file = e.dataTransfer.files?.[0];
          if (file) handleFile(file);
        }}
        className={[
          "group flex cursor-pointer flex-col items-center justify-center rounded-2xl border px-8 py-16 text-center transition-all",
          isDragging
            ? "border-signal bg-signal/5 shadow-glow"
            : "border-ink-line bg-ink-card hover:border-signal/50",
          disabled && "pointer-events-none opacity-50",
        ]
          .filter(Boolean)
          .join(" ")}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_EXT.join(",")}
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
            e.target.value = "";
          }}
        />
        <UploadCloud
          className={["mb-4 h-10 w-10 transition-colors", isDragging ? "text-signal" : "text-paper-dim"].join(" ")}
          strokeWidth={1.5}
        />
        <p className="font-display text-xl text-paper">Drop your audio here</p>
        <p className="mt-2 text-sm text-paper-dim">MP3 · WAV · M4A · FLAC · OGG</p>
        <p className="mt-6 text-sm text-signal underline-offset-4 group-hover:underline">Browse files</p>
      </div>

      {error && (
        <div className="mt-3 flex items-start gap-2 rounded-lg border border-flat/30 bg-flat/10 px-3 py-2 text-sm text-flat">
          <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
