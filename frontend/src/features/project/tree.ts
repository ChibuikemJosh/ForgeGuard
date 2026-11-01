import type { ProjectManifest } from "./types";

export interface TreeNode {
  name: string;
  path: string;
  kind: "folder" | "file";
  children?: TreeNode[];
}

const FOLDER_COLORS: Record<string, string> = {
  app: "text-sky-400", api: "text-rose-400", schemas: "text-violet-400",
  services: "text-amber-400", db: "text-emerald-400", core: "text-teal-400",
  tests: "text-green-400", routes: "text-rose-400", src: "text-green-500",
  components: "text-yellow-400", docs: "text-cyan-400",
};
const FOLDER_PALETTE = ["text-sky-400", "text-rose-400", "text-amber-400", "text-emerald-400", "text-violet-400", "text-cyan-400", "text-orange-400", "text-teal-400"];

export function folderColor(name: string): string {
  const known = FOLDER_COLORS[name.toLowerCase()];
  if (known) return known;
  let h = 0;
  for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return FOLDER_PALETTE[h % FOLDER_PALETTE.length];
}

/** Build a folder tree from manifest paths. Folders first, then A–Z. */
export function buildTree(manifest: ProjectManifest): TreeNode[] {
  const root: TreeNode = { name: manifest.name, path: "", kind: "folder", children: [] };
  for (const file of manifest.files) {
    const parts = file.path.split("/").filter(Boolean);
    let cur = root;
    parts.forEach((part, i) => {
      const isFile = i === parts.length - 1;
      const path = parts.slice(0, i + 1).join("/");
      let next = cur.children!.find((c) => c.path === path);
      if (!next) {
        next = { name: part, path, kind: isFile ? "file" : "folder", ...(isFile ? {} : { children: [] }) };
        cur.children!.push(next);
      }
      cur = next;
    });
  }
  const sortNodes = (nodes: TreeNode[]) => {
    nodes.sort((a, b) => (a.kind === b.kind ? a.name.localeCompare(b.name) : a.kind === "folder" ? -1 : 1));
    nodes.forEach((n) => { if (n.children) sortNodes(n.children); });
  };
  sortNodes(root.children ?? []);
  return root.children ?? [];
}

export function subtreeHasFindings(node: TreeNode, findingFiles: ReadonlyMap<string, number>): boolean {
  if (node.kind === "file") return (findingFiles.get(node.path) ?? 0) > 0;
  return (node.children ?? []).some((c) => subtreeHasFindings(c, findingFiles));
}

export function filterTree(nodes: TreeNode[], query: string): TreeNode[] {
  const q = query.trim().toLowerCase();
  if (!q) return nodes;
  const out: TreeNode[] = [];
  for (const n of nodes) {
    if (n.kind === "file") { if (n.name.toLowerCase().includes(q)) out.push(n); }
    else {
      const kids = filterTree(n.children ?? [], q);
      if (kids.length || n.name.toLowerCase().includes(q)) out.push({ ...n, children: kids.length ? kids : n.children });
    }
  }
  return out;
}
