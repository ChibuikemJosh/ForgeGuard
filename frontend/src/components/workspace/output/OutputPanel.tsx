import { useMemo } from "react";
import type { ApiLogEntry, InvestigationResult } from "../../../features/project/types";
import type { ProjectManifest, SourceGraph } from "../../../features/project/types";
import type { SkippedFile } from "../../../features/project/zipFolder";
import { buildProblems } from "../../../features/project/problems";
import { ActivityTab } from "./ActivityTab";
import { ProblemsTab } from "./ProblemsTab";
import { ApiLogTab } from "./ApiLogTab";

export type OutputTab = "activity" | "problems" | "api";

interface Props {
  graph: SourceGraph | null;
  manifest: ProjectManifest | null;
  investigation: InvestigationResult | null;
  uploadSkipped: SkippedFile[];
  logs: ApiLogEntry[];
  running: boolean;
  busy: boolean;
  activeTab: OutputTab;
  onTabChange: (t: OutputTab) => void;
  onClose: () => void;
  onOpenFile: (path: string) => void;
}

export function OutputPanel({ graph, manifest, investigation, uploadSkipped, logs, running, busy, activeTab, onTabChange, onClose, onOpenFile }: Props) {
  const problems = useMemo(() => buildProblems({ graph, manifest, investigation, uploadSkipped }), [graph, manifest, investigation, uploadSkipped]);
  const showApi = import.meta.env.DEV;
  const tabs: { id: OutputTab; label: string }[] = [
    { id: "activity", label: "Activity" },
    { id: "problems", label: problems.length ? `Problems (${problems.length})` : "Problems" },
    ...(showApi ? [{ id: "api" as OutputTab, label: "API log" }] : []),
  ];
  const active = tabs.some((t) => t.id === activeTab) ? activeTab : "activity";
  return (
    <section className="flex h-full flex-col overflow-hidden rounded-lg border border-line bg-panel" aria-label="Output">
      <header className="flex items-center border-b border-line px-2 py-1">
        <div role="tablist" aria-label="Output" className="flex items-center gap-1">
          {tabs.map((t) => (
            <button key={t.id} type="button" role="tab" aria-selected={active === t.id} onClick={() => onTabChange(t.id)}
              className={`rounded px-2.5 py-1 font-mono text-[10px] focus-visible:outline-2 focus-visible:outline-ide-blue ${active === t.id ? "bg-ide-active text-zinc-100" : "text-zinc-500 hover:text-zinc-300"}`}>{t.label}</button>
          ))}
        </div>
        {busy ? <span className="ml-2 font-mono text-[9px] text-ember-bright">working…</span> : null}
        <button type="button" onClick={onClose} className="ml-auto px-1 text-zinc-500 hover:text-zinc-200" aria-label="Close output">×</button>
      </header>
      <div className="workspace-scroll min-h-0 flex-1 overflow-auto" role="tabpanel">
        {active === "activity" ? <ActivityTab steps={investigation?.steps ?? []} running={running} /> : null}
        {active === "problems" ? <ProblemsTab problems={problems} onOpenFile={onOpenFile} /> : null}
        {active === "api" && showApi ? <ApiLogTab logs={logs} /> : null}
      </div>
    </section>
  );
}
