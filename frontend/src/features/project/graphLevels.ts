import dagre from "@dagrejs/dagre";
import type { SourceGraph, SourceGraphNode } from "./types";

export interface GraphGroup {
  key: string;
  name: string;
  files: SourceGraphNode[]; // module nodes
  filePaths: string[];
  functions: number;
  routes: number;
  classes: number;
}

export const ROOT_KEY = "__root__";

export function groupKeyForPath(filePath: string | null): string {
  if (!filePath) return ROOT_KEY;
  const parts = filePath.split("/").filter(Boolean);
  return parts.length <= 1 ? ROOT_KEY : parts[0];
}

export function buildGroups(graph: SourceGraph): GraphGroup[] {
  const modules = graph.nodes.filter((n) => n.type === "module" && n.file_path);
  const byKey = new Map<string, SourceGraphNode[]>();
  for (const m of modules) {
    const k = groupKeyForPath(m.file_path);
    byKey.set(k, [...(byKey.get(k) ?? []), m]);
  }
  const groups: GraphGroup[] = [...byKey.entries()].map(([key, files]) => {
    const paths = files.map((f) => f.file_path!).sort();
    const inGroup = graph.nodes.filter((n) => n.file_path && paths.includes(n.file_path));
    return {
      key,
      name: key === ROOT_KEY ? "Root modules" : `${key}/`,
      files: [...files].sort((a, b) => (a.file_path ?? "").localeCompare(b.file_path ?? "")),
      filePaths: paths,
      functions: inGroup.filter((n) => n.type === "function" || n.type === "method").length,
      routes: inGroup.filter((n) => n.type === "route").length,
      classes: inGroup.filter((n) => n.type === "class").length,
    };
  });
  groups.sort((a, b) => (a.key === ROOT_KEY ? -1 : b.key === ROOT_KEY ? 1 : a.name.localeCompare(b.name)));
  return groups;
}

export interface AggEdge { source: string; target: string; count: number; weak: boolean; types: string[] }

const AGG_TYPES = new Set(["IMPORTS", "DEPENDS_ON", "CALLS"]);

export function aggregateEdges(
  graph: SourceGraph,
  keyOfNode: (n: SourceGraphNode) => string | null,
  ids: ReadonlySet<string>,
): AggEdge[] {
  const nodeById = new Map(graph.nodes.map((n) => [n.id, n]));
  const map = new Map<string, AggEdge>();
  for (const e of graph.edges) {
    if (!e.target || !AGG_TYPES.has(e.type)) continue;
    const s = nodeById.get(e.source); const t = nodeById.get(e.target);
    if (!s || !t) continue;
    const sk = keyOfNode(s); const tk = keyOfNode(t);
    if (!sk || !tk || sk === tk || !ids.has(sk) || !ids.has(tk)) continue;
    const id = `${sk}→${tk}`;
    const cur = map.get(id) ?? { source: sk, target: tk, count: 0, weak: false, types: [] };
    cur.count += 1;
    if (e.status !== "resolved") cur.weak = true;
    if (!cur.types.includes(e.type)) cur.types.push(e.type);
    map.set(id, cur);
  }
  return [...map.values()];
}

/** Dagre positions for a small node/edge set. Returns top-left coords. */
export function dagrePositions(
  ids: string[],
  edges: { source: string; target: string }[],
  w = 218, h = 118,
): Map<string, { x: number; y: number }> {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: "TB", nodesep: 36, ranksep: 52, marginx: 12, marginy: 12 });
  g.setDefaultEdgeLabel(() => ({}));
  const idSet = new Set(ids);
  ids.forEach((id) => g.setNode(id, { width: w, height: h }));
  edges.forEach((e) => { if (idSet.has(e.source) && idSet.has(e.target) && e.source !== e.target) g.setEdge(e.source, e.target); });
  dagre.layout(g);
  const map = new Map<string, { x: number; y: number }>();
  ids.forEach((id, i) => {
    const p = g.node(id) as { x: number; y: number } | undefined;
    map.set(id, p ? { x: p.x - w / 2, y: p.y - h / 2 } : { x: (i % 3) * (w + 40), y: Math.floor(i / 3) * (h + 40) });
  });
  return map;
}

export function symbolsInFile(graph: SourceGraph, filePath: string): SourceGraphNode[] {
  return graph.nodes.filter((n) => n.file_path === filePath && ["class", "function", "method", "route"].includes(n.type));
}
