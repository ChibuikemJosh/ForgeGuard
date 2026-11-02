import { useState } from "react";
import type { ProjectFixProposal } from "../../../features/project/types";
import { DiffViewer } from "../shared/DiffViewer";
import { SideBySideDiff } from "../shared/DiffCompare";
import { addedLinesFromDiff } from "../shared/diffLines";
import { AiInlinePulse } from "../AiLoading";

interface Props {
  hasFinding: boolean; proposal: ProjectFixProposal | null; busy: boolean; phase: string;
  onGenerate: (instructions: string) => void; onReview: (d: "approved" | "rejected", reviewer: string) => void;
  onApply: () => void; onRollback: () => void; onRerun: () => void;
  canGenerate?: boolean; wide?: boolean; highlightLine?: number | null;
}

export function FixPanel({ hasFinding, proposal, busy, phase, onGenerate, onReview, onApply, onRollback, onRerun, canGenerate = true, wide = false, highlightLine = null }: Props) {
  const [instructions, setInstructions] = useState("");
  const [reviewer, setReviewer] = useState("");
  const input = "w-full rounded border border-line bg-panel-2 px-2 py-1.5 text-[11px] text-zinc-100 focus-visible:outline-2 focus-visible:outline-ide-blue";
  const btn = "rounded px-3 py-2 text-[12px] disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-ide-blue";
  const showGenerate = !proposal;
  const showReview = proposal?.review_status === "pending";
  const showApply = proposal?.review_status === "approved" && proposal.application_status !== "applied";
  const showRollback = proposal?.application_status === "applied" && proposal.rollback_available;
  return (
    <section className="rounded-lg border border-line bg-panel p-3" aria-label="AI assisted fix">
      <h3 className="font-mono text-[10px] uppercase text-zinc-400">AI-assisted fix</h3>
      {!hasFinding ? <p className="mt-2 text-[11px] text-zinc-500">Select a finding first.</p> : (
        <>
          <label className="mt-2 block text-[11px] text-zinc-300">Ask Muse for a fix (optional instructions)
            <textarea className={`${input} mt-1`} rows={3} value={instructions} onChange={(e) => setInstructions(e.target.value)} placeholder="e.g. return 403 for non-owners" />
          </label>
          {!canGenerate ? <p className="mt-2 text-[11px] text-sev-warning">Fixes need at least one validated evidence location.</p> : null}
          {showGenerate ? <button type="button" disabled={busy || !canGenerate} onClick={() => onGenerate(instructions)} className={`${btn} mt-2 w-full bg-ember font-semibold text-white hover:bg-ember-soft`}>{phase === "proposing_fix" ? <AiInlinePulse label="Generating fix…" /> : "Generate fix"}</button> : null}
          {proposal ? (
            <div className="mt-3 flex flex-col gap-2">
              <p className="font-mono text-[9px] text-zinc-500">{proposal.file_path} · review: {proposal.review_status} · apply: {proposal.application_status} · rollback: {String(proposal.rollback_available)}</p>
              <p className="text-[11px] leading-relaxed text-zinc-300">{proposal.explanation}</p>
              {proposal.error ? <p className="font-mono text-[10px] text-sev-warning">{proposal.error}</p> : null}
              {wide ? <div className="max-h-[480px]"><p className="mb-1 font-mono text-[9px] text-zinc-500">AI proposal · review status: {proposal.review_status}</p><SideBySideDiff before={proposal.original_content} after={proposal.proposed_content} highlight={highlightLine ? { start: highlightLine, end: highlightLine } : null} added={addedLinesFromDiff(proposal.unified_diff)} /></div> : null}
              <details><summary className="cursor-pointer font-mono text-[10px] text-ember-bright">Unified diff</summary><div className="mt-1"><DiffViewer diff={proposal.unified_diff} /></div></details>
              {showReview ? (
                <>
                  <input className={input} placeholder="Reviewer name (human)" value={reviewer} onChange={(e) => setReviewer(e.target.value)} aria-label="Reviewer name" />
                  <div className="flex gap-2">
                    <button type="button" disabled={busy || !reviewer.trim()} onClick={() => onReview("approved", reviewer)} className={`${btn} flex-1 bg-ember font-semibold text-white`}>Approve</button>
                    <button type="button" disabled={busy || !reviewer.trim()} onClick={() => onReview("rejected", reviewer)} className={`${btn} flex-1 border border-line text-zinc-200`}>Reject</button>
                  </div>
                </>
              ) : null}
              {showApply ? <button type="button" disabled={busy} onClick={onApply} className={`${btn} w-full bg-ember font-semibold text-white`}>{phase === "applying" ? <AiInlinePulse label="Applying…" /> : "Apply fix"}</button> : null}
              {showRollback ? <button type="button" disabled={busy} onClick={onRollback} className={`${btn} w-full border border-line text-zinc-200`}>Rollback</button> : null}
              {proposal.application_status === "applied" ? <button type="button" disabled={busy} onClick={onRerun} className={`${btn} w-full bg-ember font-semibold text-white`}>Re-run investigation</button> : null}
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}
