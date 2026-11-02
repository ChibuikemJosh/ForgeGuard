interface Props {
  leftOpen: boolean; rightOpen: boolean;
  onToggleLeft: () => void; onToggleRight: () => void;
  onHome: () => void; projectName: string | null; onChangeProject: () => void;
}
const btn = (active: boolean) => `grid size-7 place-items-center rounded-md text-[13px] transition-colors focus-visible:outline-2 focus-visible:outline-ide-blue ${active ? "bg-ide-active text-zinc-100" : "text-zinc-500 hover:bg-ide-hover hover:text-zinc-300"}`;

export function TitleBar({ leftOpen, rightOpen, onToggleLeft, onToggleRight, onHome, projectName, onChangeProject }: Props) {
  return (
    <header className="flex h-10 shrink-0 items-center gap-2 rounded-lg border border-line bg-ide-bar px-2">
      <button type="button" onClick={onHome} className="ml-1 rounded px-1.5 py-1 font-mono text-[11px] font-semibold tracking-widest text-ember-bright hover:bg-ide-hover focus-visible:outline-2 focus-visible:outline-ide-blue">FORGE</button>
      {projectName ? (
        <span className="flex min-w-0 items-center gap-2">
          <span className="truncate text-[12px] font-medium text-zinc-200">{projectName}</span>
          <button type="button" onClick={onChangeProject} className="shrink-0 rounded border border-line px-2 py-1 font-mono text-[10px] text-zinc-300 hover:bg-ide-hover focus-visible:outline-2 focus-visible:outline-ide-blue">Change project</button>
        </span>
      ) : null}
      <div className="ml-auto flex items-center gap-0.5" role="group" aria-label="Toggle panels">
        <button type="button" className={btn(leftOpen)} onClick={onToggleLeft} aria-pressed={leftOpen} title="Toggle Primary Side Bar (Explorer)">▥</button>
        <button type="button" className={btn(rightOpen)} onClick={onToggleRight} aria-pressed={rightOpen} title="Toggle Secondary Side Bar (Findings)">▦</button>
      </div>
    </header>
  );
}
