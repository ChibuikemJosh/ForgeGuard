import { AgentActivity } from "../project/AgentActivity";
import type { InvestigationStep } from "../../../features/project/types";

export function ActivityTab({ steps, running }: { steps: InvestigationStep[]; running: boolean }) {
  return (
    <div className="p-2">
      <AgentActivity steps={steps} running={running} />
      {!running && steps.length === 0 ? <p className="px-1 py-2 text-[11px] text-zinc-500">No agent activity yet. Run an investigation to see live steps here.</p> : null}
    </div>
  );
}
