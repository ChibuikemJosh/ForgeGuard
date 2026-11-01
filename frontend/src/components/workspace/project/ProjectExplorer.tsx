import { useMemo, useState } from "react";
import { FiChevronDown } from "react-icons/fi";
import { VscCollapseAll, VscRefresh } from "react-icons/vsc";
import type { ProjectManifest } from "../../../features/project/types";
import { buildTree, filterTree } from "../../../features/project/tree";
import { TreeRow } from "./ExplorerTree";

interface Props {
  manifest: ProjectManifest | null;
  projectName: string | null;
  findingFiles: ReadonlyMap<string, number>;
  selectedFile: string | null;
  onSelectFile: (path: string) => void;
  onRefresh: () => void;
}

const toolBtn = "grid size-6 place-items-center rounded text-zinc-400 hover:bg-ide-hover hover:text-zinc-100 focus-visible:outline-2 focus-visible:outline-ide-blue";

export function ProjectExplorer({ manifest, projectName, findingFiles, selectedFile, onSelectFile, onRefresh }: Props) {
  const [query, setQuery] = useState("");
  const [collapseTick, setCollapseTick] = useState(0);
  const [spinning, setSpinning] = useState(false);
  const tree = useMemo(() => (manifest ? buildTree(manifest) : []), [manifest]);
  const visible = useMemo(() => filterTree(tree, query), [tree, query]);

  const refresh = () => { onRefresh(); setSpinning(true); window.setTimeout(() => setSpinning(false), 600); };
  if (!manifest) return <div className="flex h-full items-center justify-center rounded-lg border border-line bg-panel p-3 text-center font-mono text-[10px] text-zinc-500">No project selected.</div>;

  return (
    <aside className="group/explorer flex h-full w-full flex-col overflow-hidden rounded-lg border border-line bg-panel font-ui" aria-label="Explorer">
      <div className="flex items-center justify-between px-3 pt-3">
        <h2 className="text-[11px] font-semibold tracking-[0.12em] text-zinc-400">EXPLORER</h2>
        <div className="flex items-center gap-0.5 opacity-0 transition-opacity group-hover/explorer:opacity-100 group-focus-within/explorer:opacity-100">
          <button type="button" title="Refresh Explorer" aria-label="Refresh Explorer" className={toolBtn} onClick={refresh}><VscRefresh className={`size-4 ${spinning ? "animate-spin" : ""}`} /></button>
          <button type="button" title="Collapse Folders in Explorer" aria-label="Collapse Folders in Explorer" className={toolBtn} onClick={() => setCollapseTick((t) => t + 1)}><VscCollapseAll className="size-4" /></button>
        </div>
      </div>
      <label className="mx-3 mt-2 flex items-center gap-2 rounded-md border border-line bg-ide-bar px-2 py-1.5 text-[12px] text-zinc-500 focus-within:border-ide-blue">
        <span aria-hidden>⌕</span>
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Filter files…" className="w-full bg-transparent text-zinc-200 outline-none placeholder:text-zinc-600" aria-label="Filter files by name" />
      </label>
      <div className="workspace-scroll group/tree mt-3 flex-1 overflow-y-auto px-1.5 pb-2">
        <p className="flex items-center gap-1 px-1.5 py-1 text-[11px] font-bold tracking-wider text-zinc-300">
          <FiChevronDown className="size-3.5 text-zinc-500" aria-hidden /> {(projectName ?? manifest.name).toUpperCase()}
          <span className="ml-auto rounded bg-ide-active px-1.5 py-0.5 font-mono text-[9px] font-normal text-zinc-400">Python · {manifest.python_file_count}</span>
        </p>
        {visible.length === 0 ? <p className="px-1.5 py-2 text-[12px] text-zinc-500">No files match.</p> : visible.map((n) => (
          <TreeRow key={n.path} node={n} depth={0} selectedFile={selectedFile} collapseTick={collapseTick} findingFiles={findingFiles} forceOpen={!!query.trim()} onSelectFile={onSelectFile} />
        ))}
      </div>
    </aside>
  );
}
