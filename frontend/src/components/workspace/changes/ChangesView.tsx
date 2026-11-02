import { useState } from "react";
import type { InvestigationFinding, ProjectFixProposal } from "../../../features/project/types";
import { FixPanel } from "../project/FixPanel";
import { DiffViewer } from "../shared/DiffViewer";

interface Props {
  finding: InvestigationFinding | null;
  proposal: ProjectFixProposal | null;
  appliedFixes: ProjectFixProposal[];
  busy: boolean;
  phase: string;
  hasProject: boolean;
  onGoInvestigate: () => void;
  onGenerate: (instructions: string) => void;
  onReview: (d: "approved" | "rejected", reviewer: string) => void;
  onApply: () => void;
  onRollback: () => void;
  onRerun: () => void;
  onDownloadPatch: () => void;
  onDownloadZip: () => void;
}

export function ChangesView({ finding, proposal, appliedFixes, busy, phase, hasProject, onGoInvestigate, onGenerate, onReview, onApply, onRollback, onRerun, onDownloadPatch, onDownloadZip }: Props) {
  const [openDiff, setOpenDiff] = useState<string | null>(null);
  const canGenerate = !!finding?.evidence.some((e) => e.status === "valid");
  const highlightLine = finding?.evidence.find((e) => e.status === "valid")?.source.line_start ?? null;
  const btn = "rounded px-3 py-2 text-[12px] disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-ide-blue";
  return (
    <div className="workspace-scroll flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto" aria-label="Changes">
      <section className="rounded-lg border border-line bg-panel p-3">
        {finding ? (
          <>
            <h3 className="text-[13px] font-semibold text-zinc-100">{finding.title}</h3>
            <p className="mt-1 font-mono text-[10px] text-zinc-500">status: {finding.status} · {finding.affected_files.join(", ")}</p>
          </>
        ) : (
          <>
            <p className="text-[12px] text-zinc-300">Select a finding on the Investigate tab</p>
            <button type="button" onClick={onGoInvestigate} className={`${btn} mt-2 bg-ember font-semibold text-white`}>Go to Investigate</button>
          </>
        )}
      </section>

      <FixPanel hasFinding={!!finding} proposal={proposal} busy={busy} phase={phase} wide canGenerate={canGenerate} highlightLine={highlightLine}
        onGenerate={onGenerate} onReview={onReview} onApply={onApply} onRollback={onRollback} onRerun={onRerun} />

      <section className="rounded-lg border border-line bg-panel p-3" aria-label="Applied changes">
        <h3 className="font-mono text-[10px] uppercase text-zinc-400">Applied changes</h3>
        {appliedFixes.length === 0 ? <p className="mt-2 text-[11px] text-zinc-500">No fixes applied yet.</p> : (
          <ul className="mt-2 flex flex-col gap-2">
            {appliedFixes.map((p) => (
              <li key={p.proposal_id} className="rounded-md border border-line bg-panel-2/60 p-2">
                <p className="font-mono text-[10px] text-zinc-200">{p.file_path}</p>
                <p className="mt-0.5 font-mono text-[9px] text-zinc-500">applied {p.applied_at ?? ""} · reviewer {p.reviewer ?? ""} · finding {p.finding_id}</p>
                <p className="mt-1 text-[11px] text-zinc-300">{p.explanation}</p>
                <button type="button" onClick={() => setOpenDiff(openDiff === p.proposal_id ? null : p.proposal_id)} className="mt-1 font-mono text-[10px] text-ember-bright underline focus-visible:outline-2 focus-visible:outline-ide-blue">View diff</button>
                {openDiff === p.proposal_id ? <div className="mt-1"><DiffViewer diff={p.unified_diff} /></div> : null}
              </li>
            ))}
          </ul>
        )}
      </section>

      {hasProject ? (
        <section className="rounded-lg border border-line bg-panel p-3" aria-label="Download">
          <h3 className="font-mono text-[10px] uppercase text-zinc-400">Download</h3>
          <div className="mt-2 flex flex-col gap-2">
            <button type="button" disabled={busy || appliedFixes.length === 0} onClick={onDownloadPatch} className={`${btn} bg-ember font-semibold text-white`}>Download changes (.patch)</button>
            <p className="text-[11px] text-zinc-500">Apply to your own repo with <span className="font-mono">git apply &lt;file&gt;</span>.</p>
            <button type="button" disabled={busy} onClick={onDownloadZip} className={`${btn} border border-line text-zinc-200`}>Download project copy (.zip)</button>
            <p className="text-[11px] text-zinc-500">The uploaded copy with fixes applied. Excludes .git, virtual environments, node_modules, .env/sensitive files and files over 1 MB, so don&apos;t copy it over your original folder.</p>
            <p className="text-[11px] text-sev-warning">Hosted copies are deleted after a few hours or when the server restarts. Download before you leave.</p>
          </div>
        </section>
      ) : null}
    </div>
  );
}
