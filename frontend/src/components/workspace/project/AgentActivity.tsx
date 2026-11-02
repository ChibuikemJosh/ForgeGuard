import type { InvestigationStep } from "../../../features/project/types";
import { AiInlinePulse } from "../AiLoading";

interface Props { steps: InvestigationStep[]; running: boolean }

const MARK: Record<InvestigationStep["status"], string> = { running: "…", ok: "✓", failed: "✕", skipped: "–" };

export function AgentActivity({ steps, running }: Props) {
  if (!running && steps.length === 0) return null;
  const current = [...steps].reverse().find((s) => s.status === "running");
  return (
    <section className="rounded-lg border border-line bg-panel p-3" aria-label="Agent activity" aria-live="polite">
      <h3 className="font-mono text-[10px] uppercase text-zinc-400">Agent activity</h3>
      {running ? <p className="mt-2 text-[11px] text-zinc-300"><AiInlinePulse label={current?.label ?? "Starting investigation…"} /></p> : null}
      <ol className="mt-2 flex flex-col gap-1">
        {steps.map((s) => (
          <li key={s.step_id} className="flex items-start gap-2 font-mono text-[10px] leading-relaxed text-zinc-400">
            <span aria-hidden className={s.status === "failed" ? "text-sev-warning" : s.status === "ok" ? "text-test-pass" : "text-ember-bright"}>{MARK[s.status]}</span>
            <span className="min-w-0 flex-1">{s.label}{s.duration_ms != null ? <span className="text-zinc-600"> · {s.duration_ms}ms</span> : null}
              {s.status === "failed" && s.message ? <span className="block text-sev-warning">{s.message}</span> : s.message && s.status !== "running" ? <span className="block text-zinc-500">{s.message}</span> : null}
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}
