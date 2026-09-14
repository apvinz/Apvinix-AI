import { Music, Guitar, Piano, Users } from "lucide-react";
import type { TranscriptionMode } from "../types/api";

interface ModeDef {
  id: TranscriptionMode;
  title: string;
  tagline: string;
  description: string;
  icon: typeof Music;
}

const MODES: ModeDef[] = [
  {
    id: "melody",
    title: "Melody",
    tagline: "Main vocal / lead melody",
    description: "Extract the main melody as a clean single-staff notation.",
    icon: Music,
  },
  {
    id: "melody_chords",
    title: "Sing & Play",
    tagline: "Melody + chord symbols",
    description: "Melody staff with chord symbols above it, for accompaniment.",
    icon: Guitar,
  },
  {
    id: "piano",
    title: "Piano",
    tagline: "Grand staff arrangement",
    description: "Melody, harmony and bass arranged into a playable piano score.",
    icon: Piano,
  },
  {
    id: "full_song",
    title: "Full Song",
    tagline: "Full band score",
    description: "Vocals, guitar, bass, drums and piano as individual staves.",
    icon: Users,
  },
];

interface Props {
  availableModes: TranscriptionMode[];
  selected: TranscriptionMode;
  onSelect: (mode: TranscriptionMode) => void;
}

export function ModeSelector({ availableModes, selected, onSelect }: Props) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {MODES.map((mode) => {
        const available = availableModes.includes(mode.id);
        const isSelected = selected === mode.id;
        const Icon = mode.icon;
        return (
          <button
            key={mode.id}
            type="button"
            disabled={!available}
            onClick={() => available && onSelect(mode.id)}
            className={[
              "relative flex flex-col items-start rounded-2xl border p-5 text-left transition-all",
              !available && "cursor-not-allowed border-ink-line bg-ink-card/40 opacity-50",
              available && isSelected && "border-signal bg-signal/5 shadow-glow",
              available && !isSelected && "border-ink-line bg-ink-card hover:border-signal/40",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            {!available && (
              <span className="absolute right-4 top-4 rounded-full border border-ink-line px-2 py-0.5 text-[10px] uppercase tracking-wide text-paper-faint">
                Coming soon
              </span>
            )}
            <Icon className={["mb-3 h-6 w-6", isSelected ? "text-signal" : "text-paper-dim"].join(" ")} strokeWidth={1.5} />
            <h4 className="font-display text-lg text-paper">{mode.title}</h4>
            <p className="mt-0.5 text-sm text-signal/80">{mode.tagline}</p>
            <p className="mt-2 text-sm text-paper-dim">{mode.description}</p>
          </button>
        );
      })}
    </div>
  );
}
