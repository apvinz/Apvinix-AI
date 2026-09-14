import { useEffect, useRef, useState } from "react";
import type { OpenSheetMusicDisplay as OSMDType } from "opensheetmusicdisplay";
import { AlertCircle, Loader2 } from "lucide-react";

interface Props {
  musicxmlUrl: string;
}

export function ScorePreview({ musicxmlUrl }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [errorMessage, setErrorMessage] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    let osmd: OSMDType | null = null;

    async function render() {
      if (!containerRef.current) return;
      setStatus("loading");
      try {
        const [{ OpenSheetMusicDisplay }, res] = await Promise.all([
          import("opensheetmusicdisplay"),
          fetch(musicxmlUrl),
        ]);
        if (!res.ok) throw new Error(`Could not load score (HTTP ${res.status})`);
        const xmlText = await res.text();

        if (cancelled || !containerRef.current) return;

        osmd = new OpenSheetMusicDisplay(containerRef.current, {
          backend: "svg",
          drawTitle: true,
          drawSubtitle: false,
          drawComposer: false,
          drawPartNames: true,
        });

        await osmd.load(xmlText);
        if (cancelled) return;
        osmd.render();
        setStatus("ready");
      } catch (err) {
        if (!cancelled) {
          setErrorMessage(err instanceof Error ? err.message : "Failed to render score.");
          setStatus("error");
        }
      }
    }

    render();
    return () => {
      cancelled = true;
    };
  }, [musicxmlUrl]);

  return (
    <div className="rounded-2xl border border-ink-line bg-paper p-4 sm:p-6">
      {status === "loading" && (
        <div className="flex min-h-[240px] items-center justify-center gap-2 text-ink/50">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="text-sm">Rendering score preview…</span>
        </div>
      )}
      {status === "error" && (
        <div className="flex min-h-[240px] flex-col items-center justify-center gap-2 text-ink/60">
          <AlertCircle className="h-6 w-6 text-flat" />
          <p className="text-sm">{errorMessage}</p>
          <p className="text-xs">You can still download the MusicXML/MIDI below and open them in MuseScore.</p>
        </div>
      )}
      <div ref={containerRef} className={status === "ready" ? "block" : "hidden"} />
    </div>
  );
}
