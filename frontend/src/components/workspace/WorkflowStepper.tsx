import { motion } from "motion/react";

export interface WorkflowStep { label: string; hint?: string }

export function WorkflowStepper({ steps, current, maxReached, onGo }: { steps: readonly WorkflowStep[]; current: number; maxReached: number; onGo: (n: number) => void }) {
  return (
    <ol className="flex flex-wrap items-center gap-1 rounded-lg border border-line bg-ide-bar px-2 py-1.5 font-ui" aria-label="Project workflow steps">
      {steps.map((step, i) => {
        const done = i < current;
        const active = i === current;
        const reachable = i <= maxReached;
        return (
          <li key={step.label} className="relative">
            <button type="button" disabled={!reachable} onClick={() => onGo(i)} aria-current={active ? "step" : undefined} title={step.hint ?? step.label}
              className={`relative rounded-md px-2.5 py-1.5 text-[11px] focus-visible:outline-2 focus-visible:outline-ide-blue disabled:opacity-40 ${active ? "text-white" : done ? "text-test-pass" : "text-zinc-400 hover:text-zinc-200"}`}>
              {active ? <motion.span layoutId="step-pill" className="absolute inset-0 rounded-md bg-ember" transition={{ type: "spring", stiffness: 400, damping: 32 }} /> : null}
              <span className="relative flex items-center gap-1.5"><span className="font-mono text-[9px]">{done ? "✓" : i + 1}</span>{step.label}</span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
