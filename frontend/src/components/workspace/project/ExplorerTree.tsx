import { useState } from "react";
import { FaFolder, FaFolderOpen, FaMarkdown, FaPython } from "react-icons/fa";
import { FiChevronDown, FiChevronRight, FiFileText, FiSettings } from "react-icons/fi";
import { folderColor, subtreeHasFindings, type TreeNode } from "../../../features/project/tree";

function FileIcon({ name }: { name: string }) {
  if (name.endsWith(".py")) return <FaPython className="size-4 shrink-0 text-[#4b8bbe]" aria-hidden />;
  if (name.endsWith(".md")) return <FaMarkdown className="size-4 shrink-0 text-[#519aba]" aria-hidden />;
  if (name.endsWith(".toml")) return <FiSettings className="size-4 shrink-0 text-amber-400" aria-hidden />;
  return <FiFileText className="size-4 shrink-0 text-zinc-400" aria-hidden />;
}

export function TreeRow({ node, depth, selectedFile, collapseTick, findingFiles, forceOpen, onSelectFile }: {
  node: TreeNode; depth: number; selectedFile: string | null; collapseTick: number;
  findingFiles: ReadonlyMap<string, number>; forceOpen: boolean; onSelectFile: (path: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [seen, setSeen] = useState(collapseTick);
  if (seen !== collapseTick) { setSeen(collapseTick); setOpen(false); }
  const isFolder = node.kind === "folder";
  const expanded = forceOpen || open;
  const selected = node.kind === "file" && node.path === selectedFile;
  const count = node.kind === "file" ? (findingFiles.get(node.path) ?? 0) : 0;
  const childHas = isFolder && subtreeHasFindings(node, findingFiles);
  return (
    <div>
      <button type="button" aria-expanded={isFolder ? expanded : undefined}
        onClick={() => { if (isFolder) setOpen(!open); else onSelectFile(node.path); }}
        className={`relative flex w-full items-center gap-1.5 rounded-sm px-1.5 py-[3px] text-left text-[12.5px] focus-visible:outline-2 focus-visible:outline-ide-blue ${selected ? "bg-ember/25 text-zinc-50" : "text-zinc-400 hover:bg-ide-hover hover:text-zinc-200"}`}
        style={{ paddingLeft: `${6 + depth * 14}px` }}>
        <span className="grid w-3.5 shrink-0 place-items-center text-zinc-500" aria-hidden>{isFolder ? (expanded ? <FiChevronDown className="size-3.5" /> : <FiChevronRight className="size-3.5" />) : null}</span>
        {isFolder ? (expanded ? <FaFolderOpen className={`size-4 shrink-0 ${folderColor(node.name)}`} aria-hidden /> : <FaFolder className={`size-4 shrink-0 ${folderColor(node.name)}`} aria-hidden />) : <FileIcon name={node.name} />}
        <span className={`truncate ${isFolder ? "font-medium text-zinc-300" : ""}`}>{node.name}</span>
        {count > 0 ? <span className="ml-auto grid min-w-4 shrink-0 place-items-center rounded-full bg-sev-critical/20 px-1 font-mono text-[9px] font-bold text-sev-critical" title={`${count} finding${count > 1 ? "s" : ""}`}>{count}</span>
          : childHas ? <span className="ml-auto size-1.5 shrink-0 rounded-full bg-sev-critical" title="Contains findings" aria-label="Contains findings" /> : null}
      </button>
      {isFolder && expanded && node.children?.length ? (
        <div className="relative">
          <span aria-hidden className="pointer-events-none absolute top-0 bottom-0 w-px bg-white/[0.07] transition-colors duration-100 group-hover/tree:bg-white/[0.18]" style={{ left: `${13 + depth * 14}px` }} />
          {node.children.map((c) => <TreeRow key={c.path} node={c} depth={depth + 1} selectedFile={selectedFile} collapseTick={collapseTick} findingFiles={findingFiles} forceOpen={forceOpen} onSelectFile={onSelectFile} />)}
        </div>
      ) : null}
    </div>
  );
}
