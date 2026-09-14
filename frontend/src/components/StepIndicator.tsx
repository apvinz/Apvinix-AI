const STEPS = ["Upload", "Analyze", "Choose", "Transcribe", "Review", "Export"] as const;

export type StepName = (typeof STEPS)[number];

export function StepIndicator({ current }: { current: StepName }) {
  const currentIndex = STEPS.indexOf(current);

  return (
    <ol className="flex items-center gap-2 sm:gap-3">
      {STEPS.map((step, i) => {
        const state = i < currentIndex ? "done" : i === currentIndex ? "active" : "upcoming";
        return (
          <li key={step} className="flex items-center gap-2 sm:gap-3">
            <div className="flex items-center gap-2">
              <span
                className={[
                  "flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-medium transition-colors",
                  state === "done" && "bg-signal text-ink",
                  state === "active" && "border border-signal text-signal",
                  state === "upcoming" && "border border-ink-line text-paper-faint",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                {state === "done" ? "✓" : i + 1}
              </span>
              <span
                className={[
                  "hidden text-sm sm:inline",
                  state === "upcoming" ? "text-paper-faint" : "text-paper",
                ].join(" ")}
              >
                {step}
              </span>
            </div>
            {i < STEPS.length - 1 && <span className="h-px w-4 bg-ink-line sm:w-8" aria-hidden />}
          </li>
        );
      })}
    </ol>
  );
}
