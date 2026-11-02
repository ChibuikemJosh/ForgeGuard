import type { Problem } from "../../../features/project/problems";

const KIND_LABEL: Record<Problem["kind"], string> = {
  parse: "Parse", unreadable: "Unreadable", skipped: "Skipped",
  unresolved: "Unresolved", truncated: "Truncated", investigation: "Investigation",
};

export function ProblemsTab({ problems, onOpenFile }: { problems: Problem[]; onOpenFile: (path: string) => void }) {
  if (problems.length === 0) {
    return <p className="p-3 text-[11px] text-zinc-400" aria-live="polite">No problems detected for this project.</p>;
  }
  return (
    <ul className="flex flex-col p-1" aria-live="polite" aria-label="Problems">
      {problems.map((p) => {
        const clickable = !!p.filePath;
        const inner = (
          <>
            <span className="shrink-0 rounded bg-panel-2 px-1.5 py-0.5 font-mono text-[9px] text-zinc-400">{KIND_LABEL[p.kind]}</span>
            <span className="min-w-0 flex-1 leading-relaxed">{p.message}</span>
          </>
        );
        return (
          <li key={p.id}>
            {clickable ? (
              <button type="button" onClick={() => onOpenFile(p.filePath!)} className="flex w-full items-start gap-2 rounded px-2 py-1.5 text-left text-[11px] text-zinc-300 hover:bg-ide-hover focus-visible:outline-2 focus-visible:outline-ide-blue">{inner}</button>
            ) : (
              <div className="flex w-full items-start gap-2 px-2 py-1.5 text-[11px] text-zinc-300">{inner}</div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
