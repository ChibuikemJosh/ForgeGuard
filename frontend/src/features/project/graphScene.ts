import type { Edge, Node } from "@xyflow/react";
import type { SourceGraph } from "./types";
import type { GraphCardFlowNode } from "../../components/workspace/project/GraphCardNode";
import { aggregateEdges, buildGroups, dagrePositions, groupKeyForPath, symbolsInFile, type GraphGroup } from "./graphLevels";

export const FOCUS_CONTAINER = "focus-container";
export const SYMBOL_CONTAINER = "symbol-container";
const edgeLabel = { fill: "#d6a05a", fontSize: 10, fontFamily: "JetBrains Mono, monospace" } as const;
export type SceneNode = GraphCardFlowNode | Node;

export interface SceneFocus { group: string | null; file: string | null }
export interface SceneContext {
  findingFiles: ReadonlyMap<string, number>;
  highlighted: ReadonlySet<string>;
  selectedNodeId: string | null;
  selectedFile: string | null;
}

function groupFindings(g: GraphGroup, ctx: SceneContext): number {
  return g.filePaths.reduce((n, p) => n + (ctx.findingFiles.get(p) ?? 0), 0);
}

export function buildScene(graph: SourceGraph, focus: SceneFocus, ctx: SceneContext): { nodes: SceneNode[]; edges: Edge[]; groups: GraphGroup[] } {
  const groups = buildGroups(graph);
  const byKey = new Map(groups.map((g) => [g.key, g]));
  const focused = focus.group ? byKey.get(focus.group) ?? null : null;
  const groupId = (k: string) => `group:${k}`;
  const agg = aggregateEdges(graph, (n) => (n.file_path ? groupId(groupKeyForPath(n.file_path)) : null), new Set(groups.map((g) => groupId(g.key))));
  const homePos = dagrePositions(groups.map((g) => groupId(g.key)), agg, 218, 118);
  // Fallback grid if dagre collapses single row too tightly is fine; keep dagre result.

  const groupNodes: GraphCardFlowNode[] = groups.map((g) => {
    const fc = groupFindings(g, ctx);
    return {
      id: groupId(g.key), type: "graphCard", position: homePos.get(groupId(g.key)) ?? { x: 0, y: 0 },
      zIndex: focused && g.key !== focused.key ? 1 : 3, selected: focused?.key === g.key,
      data: {
        variant: "layer", eyebrow: "LAYER", name: g.name,
        desc: focused?.key === g.key ? `${g.files.length} files · expanded below ↓` : "Click to explore modules →",
        meta: `${g.files.length} files · ${g.functions} functions · ${g.routes} routes`,
        dimmed: !!focused && g.key !== focused.key, glow: !!ctx.highlighted.size && fc > 0, findingCount: fc, routeCount: g.routes,
      },
    };
  });

  const edges: Edge[] = agg.map((e) => {
    const active = !!focused && (e.source === groupId(focused.key) || e.target === groupId(focused.key));
    return {
      id: `agg-${e.source}-${e.target}`, source: e.source, target: e.target, type: "default",
      label: e.weak ? `${e.count} · unresolved` : String(e.count),
      animated: active, zIndex: active ? 2 : 0,
      style: e.weak ? { stroke: "#8a6d4b", strokeWidth: 1, strokeDasharray: "5 4", opacity: focused && !active ? 0.12 : 0.55 }
        : focused ? (active ? { stroke: "#c99a5b", strokeWidth: 1.8 } : { stroke: "#8a6d4b", strokeWidth: 1, opacity: 0.14 })
        : { stroke: "#8a6d4b", strokeWidth: 1.4 },
      labelStyle: focused && !active ? { ...edgeLabel, opacity: 0.15 } : edgeLabel,
      labelBgStyle: { fill: "#131315", fillOpacity: focused && !active ? 0.3 : 0.9 },
    } as Edge;
  });

  if (!focused) return { nodes: groupNodes, edges, groups };

  // Level 1: files of focused group inside a container expanding from its home.
  const fileIds = focused.files.map((f) => f.id);
  const fileAgg = aggregateEdges(graph, (n) => (n.file_path && focused.filePaths.includes(n.file_path) ? focused.files.find((f) => f.file_path === n.file_path)?.id ?? null : null), new Set(fileIds));
  const localPos = dagrePositions(fileIds, fileAgg, 218, 118);
  const xs = fileIds.map((id) => localPos.get(id)?.x ?? 0); const ys = fileIds.map((id) => localPos.get(id)?.y ?? 0);
  const cW = Math.max(280, (Math.max(...xs, 0) - Math.min(...xs, 0)) + 218 + 48);
  const cH = Math.max(180, (Math.max(...ys, 0) - Math.min(...ys, 0)) + 118 + 72);
  const home = homePos.get(groupId(focused.key)) ?? { x: 0, y: 0 };
  const container: Node = {
    id: FOCUS_CONTAINER, type: "group", position: { x: home.x - 20, y: home.y + 132 }, draggable: false, selectable: false, focusable: false, zIndex: 1,
    style: { width: cW, height: cH, backgroundColor: "rgba(19,19,21,0.82)", border: "1px solid #4a3b28", borderRadius: 12, boxShadow: "0 24px 60px rgba(0,0,0,0.55)" }, data: {},
  };
  const minX = Math.min(...xs, 0); const minY = Math.min(...ys, 0);
  const fileNodes: GraphCardFlowNode[] = focused.files.map((f) => {
    const p = localPos.get(f.id) ?? { x: 0, y: 0 };
    const fc = ctx.findingFiles.get(f.file_path ?? "") ?? 0;
    const syms = symbolsInFile(graph, f.file_path ?? "");
    return {
      id: f.id, type: "graphCard", parentId: FOCUS_CONTAINER, extent: "parent",
      position: { x: p.x - minX + 24, y: p.y - minY + 40 }, zIndex: 3,
      selected: focus.file === f.file_path || ctx.selectedFile === f.file_path,
      data: {
        variant: "file", eyebrow: "FILE", name: f.file_path?.split("/").pop() ?? f.name,
        desc: f.file_path ?? f.name, meta: `${syms.filter((s) => s.type === "function" || s.type === "method").length} functions · ${syms.filter((s) => s.type === "route").length} routes`,
        dimmed: !!focus.file && focus.file !== f.file_path, glow: ctx.highlighted.has(f.id) || fc > 0 && !!ctx.highlighted.size, findingCount: fc,
        routeCount: syms.filter((s) => s.type === "route").length,
      },
    };
  });
  edges.push(...fileAgg.map((e) => ({
    id: `file-${e.source}-${e.target}`, source: e.source, target: e.target, type: "default" as const,
    label: e.weak ? `${e.count} · unresolved` : String(e.count),
    style: e.weak ? { stroke: "#8a6d4b", strokeWidth: 1, strokeDasharray: "5 4", opacity: 0.55 } : { stroke: "#c99a5b", strokeWidth: 1.6 },
    labelStyle: edgeLabel, labelBgStyle: { fill: "#131315", fillOpacity: 0.9 },
  })));

  // Ghost edges: focused files <-> other groups.
  const ghost = new Map<string, Edge>();
  const cross = aggregateEdges(graph, (n) => {
    if (!n.file_path) return null;
    if (focused.filePaths.includes(n.file_path)) return focused.files.find((f) => f.file_path === n.file_path)?.id ?? null;
    return groupId(groupKeyForPath(n.file_path));
  }, new Set([...fileIds, ...groups.filter((g) => g.key !== focused.key).map((g) => groupId(g.key))]));
  for (const e of cross) {
    if (e.source === e.target) continue;
    const involvesFile = fileIds.includes(e.source) || fileIds.includes(e.target);
    const involvesGroup = e.source.startsWith("group:") || e.target.startsWith("group:");
    if (!involvesFile || !involvesGroup) continue;
    ghost.set(`${e.source}-${e.target}`, {
      id: `ghost-${e.source}-${e.target}`, source: e.source, target: e.target, label: "imports", type: "default",
      style: { stroke: "#8a6d4b", strokeWidth: 1.2, strokeDasharray: "3 6", opacity: 0.45 },
      labelStyle: { ...edgeLabel, opacity: 0.6 }, labelBgStyle: { fill: "#131315", fillOpacity: 0.7 },
    } as Edge);
  }
  edges.push(...ghost.values());

  if (!focus.file) return { nodes: [...groupNodes, container, ...fileNodes], edges, groups };

  // Level 2: symbols of focused file.
  const symbols = symbolsInFile(graph, focus.file);
  if (!symbols.length) return { nodes: [...groupNodes, container, ...fileNodes], edges, groups };
  const symIds = new Set(symbols.map((s) => s.id));
  const symEdgesRaw = graph.edges.filter((e) => e.target && symIds.has(e.source) && symIds.has(e.target) && ["CALLS", "DEFINES", "HANDLES_ROUTE", "DEFINES_METHOD"].includes(e.type));
  const symPos = dagrePositions(symbols.map((s) => s.id), symEdgesRaw.map((e) => ({ source: e.source, target: e.target as string })), 218, 118);
  const sxs = symbols.map((s) => symPos.get(s.id)?.x ?? 0); const sys = symbols.map((s) => symPos.get(s.id)?.y ?? 0);
  const sMinX = Math.min(...sxs, 0); const sMinY = Math.min(...sys, 0);
  const focusedFileNode = fileNodes.find((f) => f.data.desc === focus.file);
  const symContainer: Node = {
    id: SYMBOL_CONTAINER, type: "group", position: { x: container.position.x + (focusedFileNode?.position.x ?? 24) - 12, y: container.position.y + cH + 16 },
    draggable: false, selectable: false, focusable: false, zIndex: 1,
    style: { width: Math.max(280, (Math.max(...sxs, 0) - sMinX) + 218 + 48), height: Math.max(180, (Math.max(...sys, 0) - sMinY) + 118 + 72), backgroundColor: "rgba(19,19,21,0.88)", border: "1px solid #4a3b28", borderRadius: 12, boxShadow: "0 24px 60px rgba(0,0,0,0.55)" }, data: {},
  };
  const symNodes: GraphCardFlowNode[] = symbols.map((s) => {
    const p = symPos.get(s.id) ?? { x: 0, y: 0 };
    return {
      id: s.id, type: "graphCard", parentId: SYMBOL_CONTAINER, extent: "parent",
      position: { x: p.x - sMinX + 24, y: p.y - sMinY + 40 }, zIndex: 4, selected: ctx.selectedNodeId === s.id,
      data: {
        variant: "symbol", eyebrow: s.type.toUpperCase(), name: s.name,
        desc: s.qualified_name ?? s.file_path ?? "", meta: s.source?.line_start ? `line ${s.source.line_start}` : (s.file_path ?? ""),
        dimmed: !!ctx.highlighted.size && !ctx.highlighted.has(s.id), glow: ctx.highlighted.has(s.id),
        findingCount: ctx.highlighted.has(s.id) && ctx.highlighted.size ? undefined : undefined,
        routeCount: s.type === "route" ? 1 : 0,
      },
    };
  });
  for (const e of symEdgesRaw) {
    const weak = e.status !== "resolved";
    edges.push({
      id: `sym-${e.id}`, source: e.source, target: e.target as string, type: "default",
      label: weak ? `${e.type} · unresolved / ambiguous (structural only)` : e.type,
      style: weak ? { stroke: "#52525b", strokeWidth: 1, strokeDasharray: "5 4", opacity: 0.55 } : { stroke: "#c99a5b", strokeWidth: 1.5 },
      labelStyle: { ...edgeLabel, fontSize: 8 }, labelBgStyle: { fill: "#131315", fillOpacity: 0.9 },
    } as Edge);
  }
  return { nodes: [...groupNodes, container, symContainer, ...fileNodes, ...symNodes], edges, groups };
}
