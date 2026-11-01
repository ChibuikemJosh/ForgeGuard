import { useCallback, useEffect, useMemo, useState } from "react";
import { Background, BackgroundVariant, Controls, MiniMap, ReactFlow, ReactFlowProvider, useEdgesState, useNodesState, useReactFlow, type NodeMouseHandler, type NodeTypes } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { SourceGraph } from "../../../features/project/types";
import { groupKeyForPath } from "../../../features/project/graphLevels";
import { buildScene, FOCUS_CONTAINER, SYMBOL_CONTAINER, type SceneNode } from "../../../features/project/graphScene";
import { GraphCardNode } from "./GraphCardNode";
import { AiLoading } from "../AiLoading";

const nodeTypes: NodeTypes = { graphCard: GraphCardNode };

interface Props {
  graph: SourceGraph | null;
  highlighted: ReadonlySet<string>;
  selectedNodeId: string | null;
  selectedFile: string | null;
  findingFiles: ReadonlyMap<string, number>;
  focusFile: string | null;
  focusTick: number;
  loading: boolean;
  error: string | null;
  onSelectNode: (id: string | null) => void;
  onSelectFile: (path: string) => void;
  onRetry: () => void;
}

function Flow(props: Props & { group: string | null; file: string | null; setGroup: (g: string | null) => void; setFile: (f: string | null) => void }) {
  const scene = useMemo(() => (props.graph ? buildScene(props.graph, { group: props.group, file: props.file }, { findingFiles: props.findingFiles, highlighted: props.highlighted, selectedNodeId: props.selectedNodeId, selectedFile: props.selectedFile }) : { nodes: [] as SceneNode[], edges: [], groups: [] }),
    [props.graph, props.group, props.file, props.findingFiles, props.highlighted, props.selectedNodeId, props.selectedFile]);
  const [nodes, setNodes, onNodesChange] = useNodesState(scene.nodes as never[]);
  const [edges, setEdges, onEdgesChange] = useEdgesState(scene.edges);
  const { fitView } = useReactFlow();
  useEffect(() => { setNodes(scene.nodes as never[]); setEdges(scene.edges); }, [scene, setNodes, setEdges]);
  useEffect(() => {
    const t = window.setTimeout(() => {
      if (props.file) void fitView({ nodes: [{ id: SYMBOL_CONTAINER }, { id: FOCUS_CONTAINER }], padding: 0.16, duration: 700, maxZoom: 1.1 });
      else if (props.group) void fitView({ nodes: [{ id: `group:${props.group}` }, { id: FOCUS_CONTAINER }], padding: 0.18, duration: 700, maxZoom: 1.1 });
      else void fitView({ padding: 0.22, duration: 700, maxZoom: 1 });
    }, 60);
    return () => window.clearTimeout(t);
  }, [props.group, props.file, fitView]);

  const handleClick: NodeMouseHandler = useCallback((_e, node) => {
    if (node.type !== "graphCard" || !props.graph) return;
    if (node.id.startsWith("group:")) { props.setGroup(node.id.slice(6)); props.setFile(null); return; }
    const src = props.graph.nodes.find((n) => n.id === node.id);
    if (!src) return;
    if (src.type === "module" && src.file_path) { props.setFile(src.file_path); props.onSelectFile(src.file_path); return; }
    props.onSelectNode(node.id);
  }, [props]);

  if (props.loading && !props.graph) return <AiLoading label="Parsing project and building graph…" detail="Reading the manifest and SourceGraph from the backend" />;
  if (!props.graph) return (
    <div className="grid h-full place-items-center rounded-lg border border-line bg-panel p-6 text-center">
      <div>{props.error ? <><p className="text-[13px] text-sev-warning" role="alert">{props.error}</p><button type="button" onClick={props.onRetry} className="mt-3 rounded bg-ember px-3 py-1.5 text-[12px] font-semibold text-white hover:bg-ember-soft">Retry</button></> : <p className="font-mono text-[10px] text-zinc-500">No SourceGraph yet.</p>}</div>
    </div>
  );
  const s = props.graph.summary;
  return (
    <div className="relative h-full min-h-0">
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onNodeClick={handleClick}
        onPaneClick={() => props.onSelectNode(null)} colorMode="dark" fitView fitViewOptions={{ padding: 0.22 }} minZoom={0.12} maxZoom={2.2} nodesConnectable={false}
        aria-label="Project source graph">
        <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#26262a" />
        <Controls position="bottom-left" showInteractive />
        <MiniMap position="bottom-right" pannable zoomable nodeColor="#2a2a2e" maskColor="rgba(10,10,11,0.72)" className="!rounded-md !border !border-line !bg-panel" />
      </ReactFlow>
      <span className="sr-only">modules {s.modules} functions {s.functions + s.methods} routes {s.routes}</span>
    </div>
  );
}

export function SourceGraphCanvas(props: Props) {
  const [group, setGroup] = useState<string | null>(null);
  const [file, setFile] = useState<string | null>(null);
  const [seenTick, setSeenTick] = useState(props.focusTick);
  if (seenTick !== props.focusTick) {
    setSeenTick(props.focusTick);
    if (props.focusFile) { setGroup(groupKeyForPath(props.focusFile)); setFile(props.focusFile); }
  }

  const back = useCallback(() => { if (file) setFile(null); else setGroup(null); }, [file]);
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === "Escape" && (group || file)) back(); };
    window.addEventListener("keydown", h); return () => window.removeEventListener("keydown", h);
  }, [back, group, file]);

  const groupName = group ? (group === "__root__" ? "Root modules" : `${group}/`) : null;
  return (
    <section className="relative flex h-full min-w-0 flex-col overflow-hidden rounded-lg border border-line bg-ide-bg font-ui" aria-label="Source graph">
      <div className="pointer-events-none absolute left-3 top-3 z-10 flex items-center gap-2">
        {group ? <button type="button" onClick={back} className="pointer-events-auto flex items-center gap-1.5 rounded-full border border-ember/60 bg-ember-deep/90 py-1.5 pl-2.5 pr-3 font-display text-[12px] font-semibold text-orange-100 shadow-lg hover:bg-ember focus-visible:outline-2 focus-visible:outline-ide-blue"><span aria-hidden>←</span> Back</button> : null}
        <nav className="pointer-events-auto flex items-center gap-1.5 rounded-full border border-line bg-panel/95 py-1.5 pl-3 pr-2 text-[12px] shadow-lg" aria-label="Breadcrumb">
          <button type="button" onClick={() => { setGroup(null); setFile(null); }} className="rounded font-medium text-zinc-300 hover:text-white focus-visible:outline-2 focus-visible:outline-ide-blue">Project</button>
          {groupName ? <><span className="text-zinc-600" aria-hidden>›</span><button type="button" onClick={() => setFile(null)} className="rounded font-display font-bold tracking-wide text-zinc-50 focus-visible:outline-2 focus-visible:outline-ide-blue">{groupName.toUpperCase()}</button></> : <span className="font-display font-bold tracking-widest text-zinc-400">PROJECT OVERVIEW</span>}
          {file ? <><span className="text-zinc-600" aria-hidden>›</span><span className="font-mono text-[11px] text-zinc-200">{file.split("/").pop()}</span><span className="text-[11px] text-zinc-500">(Esc to go back)</span></> : group ? <span className="text-[11px] text-zinc-500">(Esc to go back)</span> : null}
        </nav>
      </div>
      {group ? <div aria-hidden className="pointer-events-none absolute inset-0 z-[5] shadow-[inset_0_0_140px_rgba(0,0,0,0.6)]" /> : null}
      {props.graph?.errors.length ? <div className="absolute right-3 top-3 z-10 max-w-xs rounded border border-sev-warning/40 bg-panel/95 px-2 py-1 font-mono text-[9px] text-sev-warning">{props.graph.errors.join(" · ")}</div> : null}
      <div className="min-h-0 flex-1"><ReactFlowProvider><Flow {...props} group={group} file={file} setGroup={setGroup} setFile={setFile} /></ReactFlowProvider></div>
    </section>
  );
}
