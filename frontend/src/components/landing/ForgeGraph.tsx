import { useCallback, useMemo, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  Background,
  BackgroundVariant,
  Controls,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Edge,
  type NodeMouseHandler,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { BackendPill } from "./BackendPill";
import { ForgeNode, type ForgeFlowNode } from "./ForgeNode";
import { FORGE_NODE_BY_ID, FORGE_NODES, type ForgeNodeId } from "./data";

const nodeTypes: NodeTypes = { forge: ForgeNode };

const initialNodes: ForgeFlowNode[] = FORGE_NODES.map((node) => ({
  id: node.id,
  type: "forge",
  position: node.position,
  selected: node.id === "service",
  data: { kind: node.kind, name: node.name, file: node.file },
}));

const initialEdges: Edge[] = [
  { id: "api-service", source: "api", target: "service", label: "data", animated: true, style: { stroke: "#c2410c", strokeWidth: 1.8 }, labelStyle: { fill: "#ff7a29", fontSize: 10, fontFamily: "JetBrains Mono, monospace" }, labelBgStyle: { fill: "#131315" } },
  { id: "schema-service", source: "schema", target: "service", label: "dependency", type: "smoothstep", style: { stroke: "#71717a", strokeWidth: 1.4, strokeDasharray: "5 4" }, labelStyle: { fill: "#a1a1aa", fontSize: 10, fontFamily: "JetBrains Mono, monospace" }, labelBgStyle: { fill: "#131315" } },
  { id: "service-test", source: "service", target: "test", label: "dependency", style: { stroke: "#e4e4e7", strokeWidth: 1.4 }, labelStyle: { fill: "#d4d4d8", fontSize: 10, fontFamily: "JetBrains Mono, monospace" }, labelBgStyle: { fill: "#131315" } },
];

/**
 * Interactive React Flow preview of this repo's real slice.
 * Drag nodes, pan/zoom the canvas, click a node to inspect it below.
 */
export function ForgeGraph() {
  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);
  const [selectedId, setSelectedId] = useState<ForgeNodeId>("service");
  const selected = FORGE_NODE_BY_ID[selectedId];

  const handleNodeClick: NodeMouseHandler<ForgeFlowNode> = useCallback((_event, node) => {
    setSelectedId(node.id as ForgeNodeId);
  }, []);

  const flowLabel = useMemo(() => "Interactive Forge project graph. Drag to pan, click a node to inspect it.", []);

  return (
    <div className="relative w-full min-w-0 overflow-hidden rounded-lg border border-line bg-panel">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-3 py-2.5 sm:px-4">
        <span className="flex min-w-0 items-center gap-2 font-mono text-[10px] tracking-wide text-zinc-400 sm:text-[11px]">
          <motion.span
            className="size-1.5 rounded-full bg-ember"
            animate={{ opacity: [1, 0.2, 1] }}
            transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
            aria-hidden
          />
          LIVE WORKSPACE — PROJECT GRAPH
        </span>
        <BackendPill />
      </div>

      <div className="relative h-[300px] min-[420px]:h-[340px] sm:h-[400px]" aria-label={flowLabel}>
        {/* HUD corner ticks + scan sweep, echoing the reference's live-scene frame */}
        <span className="pointer-events-none absolute left-2 top-2 z-10 size-3 border-l border-t border-ember" aria-hidden />
        <span className="pointer-events-none absolute right-2 top-2 z-10 size-3 border-r border-t border-ember" aria-hidden />
        <span className="pointer-events-none absolute bottom-2 left-2 z-10 size-3 border-b border-l border-ember" aria-hidden />
        <motion.span
          className="pointer-events-none absolute inset-x-0 z-10 h-10 bg-[linear-gradient(to_bottom,transparent,rgba(194,65,12,0.07),transparent)]"
          animate={{ top: ["-12%", "104%"] }}
          transition={{ duration: 5.5, repeat: Infinity, ease: "linear", repeatDelay: 1.2 }}
          aria-hidden
        />
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          colorMode="dark"
          fitView
          fitViewOptions={{ padding: 0.18 }}
          minZoom={0.55}
          maxZoom={1.6}
          nodesConnectable={false}
          zoomOnScroll={false}
          proOptions={{ hideAttribution: false }}
        >
          <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="#2e2e33" />
          <Controls showInteractive={false} position="bottom-right" />
        </ReactFlow>
      </div>

      <div className="flex min-h-[46px] flex-wrap items-baseline gap-x-3 gap-y-1 border-t border-line px-3 py-3 sm:px-4" aria-live="polite">
        <AnimatePresence mode="wait" initial={false}>
          <motion.span
            key={selectedId}
            className="flex flex-wrap items-baseline gap-x-3 gap-y-1"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.22 }}
          >
            <span className="break-all font-mono text-[10px] text-ember-bright sm:text-[11px]">{selected.file}</span>
            <span className="text-[14px] leading-snug text-zinc-200 sm:text-[15px]">{selected.detail}</span>
          </motion.span>
        </AnimatePresence>
        <span className="ml-auto hidden font-mono text-[10px] text-zinc-500 lg:block">drag nodes · click to inspect</span>
      </div>
    </div>
  );
}
