import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Toaster } from "sonner";
import { StatusBar } from "../components/workspace/StatusBar";
import { ResizeHandle } from "../components/workspace/ResizeHandle";
import { TitleBar } from "../components/workspace/TitleBar";
import { WorkflowStepper, type WorkflowStep } from "../components/workspace/WorkflowStepper";
import { AiInlinePulse } from "../components/workspace/AiLoading";
import { useProjectWorkflow } from "../hooks/useProjectWorkflow";
import { ProjectPicker } from "../components/workspace/project/ProjectPicker";
import { ProjectExplorer } from "../components/workspace/project/ProjectExplorer";
import { SourceGraphCanvas } from "../components/workspace/project/SourceGraphCanvas";
import { ProjectCodeViewer } from "../components/workspace/project/ProjectCodeViewer";
import { RulePanel } from "../components/workspace/project/RulePanel";
import { FindingsPanel } from "../components/workspace/project/FindingsPanel";
import { FixPanel } from "../components/workspace/project/FixPanel";

const clamp = (v: number, min: number, max: number) => Math.min(max, Math.max(min, v));
const LEFT = { def: 260, min: 180, max: 420 };
const RIGHT = { def: 340, min: 240, max: 560 };
const BOTTOM = { def: 224, min: 120, max: 520 };
type CenterTab = "graph" | "code" | "split";
const STEPS: readonly WorkflowStep[] = [
  { label: "Load" }, { label: "Map" }, { label: "Investigate" },
  { label: "Understand" }, { label: "Review" }, { label: "Apply" }, { label: "Verify" },
];

export default function Workspace() {
  const navigate = useNavigate();
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);
  const [bottomOpen, setBottomOpen] = useState(false);
  const [leftWidth, setLeftWidth] = useState(LEFT.def);
  const [rightWidth, setRightWidth] = useState(RIGHT.def);
  const [bottomHeight, setBottomHeight] = useState(BOTTOM.def);
  const [centerTab, setCenterTab] = useState<CenterTab>("split");
  const [splitPct, setSplitPct] = useState(52);
  const [focusFile, setFocusFile] = useState<string | null>(null);
  const [focusTick, setFocusTick] = useState(0);
  const proj = useProjectWorkflow();
  const { state: pstate, actions: pactions } = proj;

  useEffect(() => { pactions.checkHealth(); pactions.loadSamples(); /* eslint-disable-next-line */ }, []);

  const findingFiles = useMemo(() => {
    const m = new Map<string, number>();
    pstate.investigation?.findings.forEach((f) => f.affected_files.forEach((x) => m.set(x, (m.get(x) ?? 0) + 1)));
    return m;
  }, [pstate.investigation]);

  const highlightedNodes = useMemo(() => {
    const s = new Set<string>();
    if (pstate.selectedFinding) {
      pstate.selectedFinding.related_graph_nodes.forEach((n) => s.add(n));
      pstate.graph?.nodes.forEach((n) => { if (n.file_path && pstate.selectedFinding!.affected_files.includes(n.file_path)) s.add(n.id); });
    } else if (pstate.selectedNodeId) s.add(pstate.selectedNodeId);
    return s;
  }, [pstate.selectedFinding, pstate.graph, pstate.selectedNodeId]);

  const drillToFile = useCallback((path: string) => { setFocusFile(path); setFocusTick((t) => t + 1); }, []);

  const { current, maxReached } = useMemo(() => {
    if (!pstate.project) return { current: 0, maxReached: 0 };
    if (!pstate.graph) return { current: 1, maxReached: 1 };
    if (pstate.verifiedSummary) return { current: 6, maxReached: 6 };
    if (pstate.proposal?.application_status === "applied") return { current: 6, maxReached: 6 };
    if (pstate.proposal) return { current: 5, maxReached: 5 };
    if (pstate.selectedFinding) return { current: 4, maxReached: 4 };
    if (pstate.investigation) return { current: 3, maxReached: 3 };
    return { current: 2, maxReached: 2 };
  }, [pstate.project, pstate.graph, pstate.investigation, pstate.selectedFinding, pstate.proposal, pstate.verifiedSummary]);

  const onStep = useCallback((n: number) => {
    if (n <= 1) setCenterTab("graph");
    else if (n === 3) { setCenterTab("split"); }
    else { setRightOpen(true); setCenterTab("split"); }
  }, []);

  const busyLoading = pstate.busy && (pstate.phase === "analyzing" || pstate.phase === "investigating" || pstate.phase === "proposing_fix" || pstate.phase === "applying");

  return (
    <div className="flex h-screen flex-col gap-1.5 bg-ide-bg p-1.5 font-ui text-zinc-100">
      <a href="#workspace-graph" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-ember focus:px-3 focus:py-2 focus:text-white">Skip to graph</a>
      <Toaster theme="dark" toastOptions={{ style: { background: "#1a1a1d", border: "1px solid #262629", color: "#f4f4f5" } }} position="bottom-right" />
      <TitleBar leftOpen={leftOpen} rightOpen={rightOpen} bottomOpen={bottomOpen} onToggleLeft={() => setLeftOpen((v) => !v)} onToggleRight={() => setRightOpen((v) => !v)} onToggleBottom={() => setBottomOpen((v) => !v)} onHome={() => navigate("/")} projectName={pstate.project?.name ?? null} onChangeProject={pactions.changeProject} />
      <div className="flex min-h-0 flex-1 gap-1.5">
        {leftOpen && pstate.project ? (<>
          <div className="shrink-0" style={{ width: leftWidth }}>
            <ProjectExplorer manifest={pstate.manifest} projectName={pstate.project.name} findingFiles={findingFiles} selectedFile={pstate.selectedFile} onRefresh={pactions.refresh}
              onSelectFile={(p) => { pactions.openFile(p); drillToFile(p); setCenterTab("split"); }} />
          </div>
          <ResizeHandle axis="x" label="Resize Explorer sidebar" onResize={(d) => setLeftWidth((w) => clamp(w + d, LEFT.min, LEFT.max))} />
        </>) : null}
        <div className="flex min-w-0 flex-1 flex-col gap-1.5" id="workspace-graph">
          {!pstate.project ? (
            <div className="min-h-0 flex-1 overflow-auto">
              <ProjectPicker samples={pstate.samples} busy={pstate.busy} onUseSample={pactions.useSample} onUploadFolder={pactions.uploadFolder} />
              {pstate.error ? <p className="mt-2 flex items-center gap-2 rounded-lg border border-sev-warning/30 bg-panel px-3 py-2 font-mono text-[11px] text-sev-warning" role="alert">{pstate.error}<button type="button" onClick={pactions.clearError} className="underline">Dismiss</button></p> : null}
            </div>
          ) : (<>
            <WorkflowStepper steps={STEPS} current={current} maxReached={maxReached} onGo={onStep} />
            {pstate.verifiedSummary ? <p className="rounded-lg border border-line bg-panel px-3 py-1.5 text-[11px] text-zinc-300" aria-live="polite">Verify: {pstate.verifiedSummary}</p> : null}
            {pstate.phase === "investigating" ? <div className="flex shrink-0 items-center gap-2 rounded-lg border border-ember/30 bg-panel px-3 py-2 font-mono text-[10px] text-zinc-300"><AiInlinePulse label={`Muse is investigating · ${pstate.manifest?.python_file_count ?? "…"} Python files…`} /></div> : null}
            <div className="flex items-center gap-1" role="tablist" aria-label="Center view">
              {([["graph", "Graph"], ["code", pstate.selectedFile ?? "Code"], ["split", "Split"]] as [CenterTab, string][]).map(([id, label]) => (
                <button key={id} type="button" role="tab" aria-selected={centerTab === id} onClick={() => setCenterTab(id)} className={`rounded px-2.5 py-1 font-mono text-[10px] focus-visible:outline-2 focus-visible:outline-ide-blue ${centerTab === id ? "bg-ide-active text-zinc-100" : "text-zinc-500 hover:text-zinc-300"}`}>{label}</button>
              ))}
              <span className="ml-auto hidden font-mono text-[9px] text-zinc-600 lg:block" aria-live="polite">{pstate.phase}</span>
              {pstate.graph ? <button type="button" disabled={pstate.busy} onClick={pactions.analyze} className="rounded border border-line px-2 py-1 font-mono text-[10px] text-zinc-300 hover:bg-ide-hover disabled:opacity-40">Re-analyze</button> : null}
              {pstate.error && pstate.graph ? <span className="flex items-center gap-2 font-mono text-[10px] text-sev-warning" role="alert">{pstate.error}<button type="button" onClick={pactions.clearError} className="underline">Dismiss</button></span> : null}
            </div>
            <div className="flex min-h-0 flex-1 gap-1.5">
              {centerTab !== "code" ? <div className="min-w-0" style={centerTab === "split" ? { width: `${splitPct}%` } : { flex: 1 }}>
                <SourceGraphCanvas graph={pstate.graph} highlighted={highlightedNodes} selectedNodeId={pstate.selectedNodeId} selectedFile={pstate.selectedFile}
                  findingFiles={findingFiles} focusFile={focusFile} focusTick={focusTick} loading={pstate.phase === "analyzing"} error={!pstate.graph ? pstate.error : null}
                  onRetry={pactions.analyze} onSelectFile={(p) => { pactions.openFile(p); }}
                  onSelectNode={(id) => { pactions.selectNode(id); if (id) setCenterTab("split"); }} />
              </div> : null}
              {centerTab === "split" ? <ResizeHandle axis="x" label="Resize graph/code split" onResize={(d) => setSplitPct((p) => clamp(p + d / 10, 25, 75))} /> : null}
              {centerTab !== "graph" ? <div className="min-w-0 flex-1"><ProjectCodeViewer file={pstate.fileContent} highlightLine={pstate.highlightLine} /></div> : null}
            </div>
          </>)}
          {bottomOpen ? (<>
            <ResizeHandle axis="y" label="Resize bottom panel" onResize={(d) => setBottomHeight((h) => clamp(h - d, BOTTOM.min, BOTTOM.max))} />
            <div className="shrink-0" style={{ height: bottomHeight }}>
              <section className="flex h-full flex-col overflow-hidden rounded-lg border border-line bg-panel" aria-label="Output">
                <header className="flex items-center border-b border-line px-3 py-1.5"><span className="font-mono text-[10px] uppercase text-zinc-400">Output · API calls</span>{busyLoading ? <span className="ml-2 font-mono text-[9px] text-ember-bright">working…</span> : null}<button type="button" onClick={() => setBottomOpen(false)} className="ml-auto text-zinc-500 hover:text-zinc-200" aria-label="Close output">×</button></header>
                <div className="workspace-scroll min-h-0 flex-1 overflow-auto p-2 font-mono text-[10px] text-zinc-400">
                  {pstate.logs.length === 0 ? <p>No API calls yet.</p> : pstate.logs.map((l) => <div key={l.id}>{l.at} · {l.method} {l.path} · {l.status} · {l.durationMs}ms</div>)}
                </div>
              </section>
            </div>
          </>) : null}
        </div>
        {rightOpen && pstate.project ? (<>
          <ResizeHandle axis="x" label="Resize Findings sidebar" onResize={(d) => setRightWidth((w) => clamp(w - d, RIGHT.min, RIGHT.max))} />
          <div className="shrink-0" style={{ width: rightWidth }}>
            <div className="workspace-scroll flex h-full flex-col gap-1.5 overflow-y-auto">
              <RulePanel rules={pstate.rules} rule={pstate.rule} onSelect={pactions.setRule} busy={pstate.busy} canInvestigate={!!pstate.project && !!pstate.graph && !!pstate.rule} onInvestigate={pactions.investigate} onCancel={pactions.cancel} investigating={pstate.phase === "investigating"} pythonCount={pstate.manifest?.python_file_count ?? null} />
              <FindingsPanel result={pstate.investigation} selected={pstate.selectedFinding} onSelect={(f) => { pactions.selectFinding(f); if (f.affected_files[0]) drillToFile(f.affected_files[0]); setCenterTab("split"); setRightOpen(true); }} />
              <FixPanel hasFinding={!!pstate.selectedFinding} proposal={pstate.proposal} busy={pstate.busy} phase={pstate.phase} onGenerate={pactions.generateFix} onReview={pactions.review} onApply={pactions.apply} onRollback={pactions.rollback} onRerun={pactions.rerun} />
            </div>
          </div>
        </>) : null}
      </div>
      <StatusBar backendOk={pstate.backendOk} projectName={pstate.project?.name ?? null} fileName={pstate.selectedFile} investigationStatus={pstate.investigation?.status ?? null} phase={pstate.phase} reviewStatus={pstate.proposal?.review_status ?? null} applicationStatus={pstate.proposal?.application_status ?? null} />
    </div>
  );
}
