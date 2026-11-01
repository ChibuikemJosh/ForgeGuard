import { Suspense, lazy, useEffect, useRef } from "react";
import type { FileContentResponse } from "../../../features/project/types";
import { PlainLines } from "../shared/PlainLines";

const ShikiLines = lazy(() => import("../shared/ShikiLines"));

interface Props { file: FileContentResponse | null; highlightLine: number | null }

export function ProjectCodeViewer({ file, highlightLine }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const highlight = highlightLine ? { start: highlightLine, end: highlightLine } : null;
  useEffect(() => {
    if (!highlightLine || !scrollRef.current) return;
    scrollRef.current.querySelector(`[data-line="${highlightLine}"]`)?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [highlightLine, file]);
  if (!file) return <div className="grid h-full place-items-center rounded-lg border border-line bg-panel p-6 text-center"><p className="font-mono text-[10px] text-zinc-500">Select a file, finding, or graph node to view code.</p></div>;
  const lines = file.content.split("\n");
  return (
    <section className="flex h-full min-h-0 flex-col overflow-hidden rounded-lg border border-line bg-[#0d0d0f]" aria-label="Project code viewer">
      <header className="flex flex-wrap items-center gap-2 border-b border-line px-2 py-1.5">
        <span className="font-mono text-[10px] text-zinc-200">{file.path}</span>
        <span className="font-mono text-[9px] text-zinc-500">sha256 {file.sha256.slice(0, 12)}…</span>
        {highlightLine ? <span className="rounded bg-sev-critical/15 px-1.5 py-0.5 font-mono text-[9px] text-sev-critical">line {highlightLine}</span> : null}
      </header>
      <div ref={scrollRef} className="workspace-scroll min-h-0 flex-1 overflow-auto py-2">
        <Suspense fallback={<PlainLines lines={lines} highlight={highlight} />}>
          <ShikiLines code={file.content} highlight={highlight} />
        </Suspense>
      </div>
    </section>
  );
}
