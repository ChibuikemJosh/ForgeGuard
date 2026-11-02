import { useEffect, useRef } from "react";
import type { SampleProject } from "../../../features/project/types";

interface Props { samples: SampleProject[]; busy: boolean; onUseSample: (s: SampleProject) => void; onUploadFolder: (files: File[]) => void }

const secondaryButton = "rounded border border-line px-3 py-2 text-left font-ui text-[12px] text-zinc-200 hover:bg-ide-hover disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-ide-blue";

export function ProjectPicker({ samples, busy, onUseSample, onUploadFolder }: Props) {
  const folderRef = useRef<HTMLInputElement>(null);
  // `webkitdirectory` is not in React's input typings, so set it on the DOM node.
  useEffect(() => { folderRef.current?.setAttribute("webkitdirectory", ""); }, []);
  return (
    <section className="rounded-lg border border-line bg-panel p-4" aria-label="Pick a project">
      <h2 className="text-[13px] font-semibold text-zinc-100">Project Investigation</h2>
      <p className="mt-1 text-[11px] leading-relaxed text-zinc-400">Select a project, analyze it into a SourceGraph, pick a rule, and run the Muse investigation. Findings are potential until you review them.</p>
      <div className="mt-3 flex flex-col gap-2">
        {samples.length === 0 ? <p className="font-mono text-[10px] text-zinc-500">No samples returned by the backend.</p> : samples.map((s) => (
          <button key={s.path} type="button" disabled={busy} onClick={() => onUseSample(s)} className="rounded bg-ember px-3 py-2 text-left font-ui text-[12px] font-semibold text-white hover:bg-ember-soft disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-ide-blue">
            Use sample project: {s.name}<span className="block font-mono text-[9px] font-normal text-orange-100/80">{s.description}</span>
          </button>
        ))}
        <input ref={folderRef} type="file" multiple className="hidden" aria-label="Upload a Python project folder"
          onChange={(e) => { const files = Array.from(e.target.files ?? []); if (files.length) onUploadFolder(files); e.target.value = ""; }} />
        <button type="button" disabled={busy} onClick={() => folderRef.current?.click()} className={secondaryButton}>
          Upload project folder<span className="block font-mono text-[9px] text-zinc-500">Zipped in your browser; .git, node_modules, venvs and .env files are skipped.</span>
        </button>
        <p className="text-[11px] leading-relaxed text-zinc-500">Your Python files are sent to the Meta Muse model for analysis. Folder uploads up to 10 MB; .git, virtual environments, node_modules and .env/sensitive files are skipped. Hosted copies expire after a few hours.</p>
      </div>
    </section>
  );
}
