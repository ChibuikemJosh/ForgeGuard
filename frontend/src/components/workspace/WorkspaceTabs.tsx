export type WorkspaceTab = "investigate" | "changes";

interface Props { tab: WorkspaceTab; onChange: (t: WorkspaceTab) => void; appliedCount: number }

export function WorkspaceTabs({ tab, onChange, appliedCount }: Props) {
  const tabs: { id: WorkspaceTab; label: string }[] = [
    { id: "investigate", label: "Investigate" },
    { id: "changes", label: `Changes${appliedCount ? ` (${appliedCount})` : ""}` },
  ];
  return (
    <div className="flex shrink-0 items-center gap-1" role="tablist" aria-label="Workspace">
      {tabs.map((t) => (
        <button key={t.id} type="button" role="tab" aria-selected={tab === t.id} onClick={() => onChange(t.id)}
          className={`rounded px-3 py-1.5 font-mono text-[11px] focus-visible:outline-2 focus-visible:outline-ide-blue ${tab === t.id ? "bg-ide-active text-zinc-100" : "text-zinc-500 hover:text-zinc-300"}`}>
          {t.label}
        </button>
      ))}
    </div>
  );
}
