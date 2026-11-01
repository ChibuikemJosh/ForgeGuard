import { useCallback, useEffect, useMemo, useReducer, useRef } from "react";
import { toast } from "sonner";
import * as api from "../services/api/client";
import { zipFolder } from "../features/project/zipFolder";
import type { ApiLogEntry, FileContentResponse, InvestigationFinding, InvestigationResult, ProjectFixProposal, ProjectManifest, ProjectReference, SampleProject, SecurityRule, SourceGraph } from "../features/project/types";

export type ProjectPhase = "idle" | "project_selected" | "analyzing" | "graph_ready" | "investigating" | "findings_ready" | "proposing_fix" | "proposal_ready" | "approved" | "applying" | "applied" | "error";

export interface ProjectState {
  phase: ProjectPhase; busy: boolean; error: string | null; retryPhase: ProjectPhase;
  backendOk: boolean | null; samples: SampleProject[]; project: ProjectReference | null;
  manifest: ProjectManifest | null; graph: SourceGraph | null; rules: SecurityRule[];
  rule: SecurityRule | null; investigation: InvestigationResult | null;
  selectedFinding: InvestigationFinding | null; selectedNodeId: string | null;
  selectedFile: string | null; highlightLine: number | null; fileContent: FileContentResponse | null;
  proposal: ProjectFixProposal | null; logs: ApiLogEntry[];
  /** Backend summary word-for-word from an investigation re-run after apply. */
  verifiedSummary: string | null;
}
const initial: ProjectState = { phase: "idle", busy: false, error: null, retryPhase: "idle", backendOk: null, samples: [], project: null, manifest: null, graph: null, rules: [], rule: null, investigation: null, selectedFinding: null, selectedNodeId: null, selectedFile: null, highlightLine: null, fileContent: null, proposal: null, logs: [], verifiedSummary: null };
type Action = { type: "patch"; patch: Partial<ProjectState> } | { type: "log"; entry: ApiLogEntry };
function reducer(s: ProjectState, a: Action): ProjectState {
  if (a.type === "log") return { ...s, logs: [a.entry, ...s.logs].slice(0, 80) };
  return { ...s, ...a.patch };
}
let seq = 1;

export function useProjectWorkflow() {
  const [state, dispatch] = useReducer(reducer, initial);
  const controllers = useRef(new Set<AbortController>());
  const stateRef = useRef(state);
  useEffect(() => { stateRef.current = state; }, [state]);
  const patch = useCallback((p: Partial<ProjectState>) => dispatch({ type: "patch", patch: p }), []);
  const log = useCallback((method: string, path: string, status: number | string, durationMs: number) => {
    dispatch({ type: "log", entry: { id: seq++, at: new Date().toLocaleTimeString(), method, path, status, durationMs } });
  }, []);
  const cancel = useCallback(() => {
    controllers.current.forEach((c) => c.abort());
    controllers.current.clear();
    patch({ busy: false, phase: stateRef.current.project ? "project_selected" : "idle" });
  }, [patch]);

  const call = useCallback(async <T,>(method: string, path: string, fn: (s: AbortSignal) => Promise<T>): Promise<T> => {
    const c = new AbortController();
    controllers.current.add(c);
    const t = performance.now();
    try { const r = await fn(c.signal); log(method, path, 200, Math.round(performance.now() - t)); return r; }
    catch (e) { log(method, path, "ERR", Math.round(performance.now() - t)); throw e; }
    finally { controllers.current.delete(c); }
  }, [log]);

  const fail = useCallback((e: unknown, retry: ProjectPhase) => {
    if (e instanceof DOMException && e.name === "AbortError") { patch({ busy: false }); return; }
    const msg = e instanceof Error ? e.message : "Request failed";
    patch({ busy: false, error: msg, phase: "error", retryPhase: retry }); toast.error(msg);
  }, [patch]);

  const checkHealth = useCallback(async () => {
    try { await call("GET", "/api/health", (s) => api.fetchBackendHealth(s)); patch({ backendOk: true }); }
    catch { patch({ backendOk: false }); }
  }, [call, patch]);

  const loadSamples = useCallback(async () => {
    try {
      const [samples, rules] = await Promise.all([
        call("GET", "/api/workspace/samples", (s) => api.listSamples(s)),
        call("GET", "/api/security/rules", (s) => api.listRules(s)),
      ]);
      patch({ samples, rules, rule: rules.find((r) => r.rule_id === "order-ownership-authorization") ?? rules[0] ?? null });
    } catch (e) { fail(e, "idle"); }
  }, [call, fail, patch]);

  const selectProjectRef = useCallback(async (ref: ProjectReference) => {
    patch({ project: ref, phase: "analyzing", busy: true, error: null, graph: null, investigation: null, proposal: null, selectedFinding: null, selectedFile: null, fileContent: null, verifiedSummary: null, manifest: null });
    try {
      const m = await call("GET", `/api/workspace/projects/${ref.project_id}/manifest`, (s) => api.getManifest(ref.project_id, s));
      patch({ manifest: m });
      const g = await call("GET", `/api/workspace/projects/${ref.project_id}/source-graph`, (s) => api.getSourceGraph(ref.project_id, s));
      patch({ busy: false, graph: g, phase: "graph_ready" });
    } catch (e) { fail(e, "idle"); }
  }, [call, fail, patch]);

  const changeProject = useCallback(() => {
    controllers.current.forEach((c) => c.abort()); controllers.current.clear();
    patch({ project: null, manifest: null, graph: null, investigation: null, proposal: null, selectedFinding: null, selectedNodeId: null, selectedFile: null, fileContent: null, highlightLine: null, error: null, busy: false, phase: "idle", verifiedSummary: null });
  }, [patch]);

  const refresh = useCallback(async () => {
    const pid = stateRef.current.project?.project_id; if (!pid) return;
    patch({ busy: true, error: null, phase: "analyzing" });
    try {
      const m = await call("GET", `/api/workspace/projects/${pid}/manifest`, (s) => api.getManifest(pid, s));
      const g = await call("GET", `/api/workspace/projects/${pid}/source-graph`, (s) => api.getSourceGraph(pid, s));
      patch({ busy: false, manifest: m, graph: g, phase: "graph_ready" });
    } catch (e) { fail(e, "project_selected"); }
  }, [call, fail, patch]);

  const useSample = useCallback(async (sample: SampleProject) => {
    patch({ busy: true, error: null });
    try { const ref = await call("POST", "/api/workspace/projects", (s) => api.openProject(sample.path, sample.name, s)); patch({ busy: false }); await selectProjectRef(ref); }
    catch (e) { fail(e, "idle"); }
  }, [call, fail, patch, selectProjectRef]);

  const uploadZip = useCallback(async (file: File) => {
    patch({ busy: true, error: null });
    try { const ref = await call("POST", "/api/workspace/projects/upload", (s) => api.uploadProjectZip(file, s)); patch({ busy: false }); await selectProjectRef(ref); toast.success(`Uploaded ${file.name}`); }
    catch (e) { fail(e, "idle"); }
  }, [call, fail, patch, selectProjectRef]);

  const uploadFolder = useCallback(async (files: File[]) => {
    patch({ busy: true, error: null });
    try {
      const { zip, fileCount, skippedCount } = await zipFolder(files);
      const ref = await call("POST", "/api/workspace/projects/upload", (s) => api.uploadProjectZip(zip, s));
      patch({ busy: false }); await selectProjectRef(ref);
      toast.success(`Uploaded ${zip.name.replace(/\.zip$/, "")} (${fileCount} files${skippedCount ? `, ${skippedCount} skipped` : ""})`);
    } catch (e) { fail(e, "idle"); }
  }, [call, fail, patch, selectProjectRef]);

  const analyze = useCallback(async () => {
    const pid = stateRef.current.project?.project_id; if (!pid) return;
    patch({ busy: true, error: null, phase: "analyzing" });
    try { const g = await call("GET", `/api/workspace/projects/${pid}/source-graph`, (s) => api.getSourceGraph(pid, s)); patch({ busy: false, graph: g, phase: "graph_ready" }); }
    catch (e) { fail(e, "project_selected"); }
  }, [call, fail, patch]);

  const openFile = useCallback(async (path: string, line?: number | null) => {
    const pid = stateRef.current.project?.project_id; if (!pid) return;
    patch({ selectedFile: path, highlightLine: line ?? null });
    try { const c = await call("GET", `/api/workspace/projects/${pid}/files/content?path=${path}`, (s) => api.getFileContent(pid, path, s)); patch({ fileContent: c }); }
    catch (e) { fail(e, stateRef.current.phase); }
  }, [call, fail, patch]);

  const investigate = useCallback(async () => {
    const st = stateRef.current; const pid = st.project?.project_id; const rule = st.rule; if (!pid || !rule) return;
    const wasApplied = st.proposal?.application_status === "applied";
    patch({ busy: true, error: null, phase: "investigating", ...(wasApplied ? {} : { proposal: null, selectedFinding: null }) });
    try {
      const r = await call("POST", `/api/workspace/projects/${pid}/investigate`, (s) => api.investigateProject(pid, rule, s));
      patch({ busy: false, investigation: r, phase: "findings_ready", ...(wasApplied ? { verifiedSummary: r.summary } : {}) });
      if (r.status === "failed") toast.error(r.errors[0] ?? r.summary);
      else toast.success(r.summary);
    } catch (e) { fail(e, "graph_ready"); }
  }, [call, fail, patch]);

  const selectFinding = useCallback((f: InvestigationFinding | null) => {
    patch({ selectedFinding: f, selectedNodeId: f?.related_graph_nodes[0] ?? null });
    if (f) { const ev = f.evidence.find((e) => e.status === "valid") ?? f.evidence[0]; if (ev) void openFile(ev.file_path, ev.source.line_start); }
  }, [openFile, patch]);

  const selectNode = useCallback((nodeId: string | null) => {
    patch({ selectedNodeId: nodeId });
    const node = stateRef.current.graph?.nodes.find((n) => n.id === nodeId);
    if (node?.file_path) void openFile(node.file_path, node.source?.line_start);
  }, [openFile, patch]);

  const generateFix = useCallback(async (instructions: string) => {
    const st = stateRef.current; const pid = st.project?.project_id; const f = st.selectedFinding; if (!pid || !f) return;
    patch({ busy: true, error: null, phase: "proposing_fix" });
    try { const p = await call("POST", `/api/workspace/projects/${pid}/findings/${f.finding_id}/fix-proposals`, (s) => api.createFixProposal(pid, f.finding_id, instructions || undefined, s)); patch({ busy: false, proposal: p, phase: "proposal_ready" }); }
    catch (e) { fail(e, "findings_ready"); }
  }, [call, fail, patch]);

  const review = useCallback(async (decision: "approved" | "rejected", reviewer: string) => {
    const p = stateRef.current.proposal; if (!p) return;
    patch({ busy: true, error: null });
    try { const r = await call("POST", `/api/workspace/fix-proposals/${p.proposal_id}/review`, (s) => api.reviewProjectFixProposal(p.proposal_id, { decision, reviewer, actor: "human" }, s)); patch({ busy: false, proposal: r, phase: decision === "approved" ? "approved" : "proposal_ready" }); }
    catch (e) { fail(e, "proposal_ready"); }
  }, [call, fail, patch]);

  const apply = useCallback(async () => {
    const p = stateRef.current.proposal; if (!p) return;
    patch({ busy: true, error: null, phase: "applying" });
    try { const r = await call("POST", `/api/workspace/fix-proposals/${p.proposal_id}/apply`, (s) => api.applyProjectFixProposal(p.proposal_id, s)); patch({ busy: false, proposal: r, phase: "applied" }); if (stateRef.current.selectedFile) void openFile(stateRef.current.selectedFile, stateRef.current.highlightLine); toast.success("Fix applied"); }
    catch (e) { fail(e, "approved"); }
  }, [call, fail, openFile, patch]);

  const rollback = useCallback(async () => {
    const p = stateRef.current.proposal; if (!p) return;
    patch({ busy: true, error: null });
    try { const r = await call("POST", `/api/workspace/fix-proposals/${p.proposal_id}/rollback`, (s) => api.rollbackProjectFixProposal(p.proposal_id, s)); patch({ busy: false, proposal: r, phase: "approved", verifiedSummary: null }); if (stateRef.current.selectedFile) void openFile(stateRef.current.selectedFile, stateRef.current.highlightLine); toast.success("Rolled back"); }
    catch (e) { fail(e, "applied"); }
  }, [call, fail, openFile, patch]);

  const rerun = useCallback(async () => { await analyze(); await investigate(); }, [analyze, investigate]);

  const actions = useMemo(() => ({
    checkHealth, loadSamples, useSample, uploadZip, uploadFolder, analyze, investigate, rerun, changeProject, refresh,
    setRule: (r: SecurityRule | null) => patch({ rule: r }),
    selectFinding, selectNode, openFile, generateFix, review, apply, rollback, cancel,
    clearError: () => patch({ error: null, phase: stateRef.current.retryPhase }),
  }), [analyze, apply, cancel, changeProject, checkHealth, generateFix, investigate, loadSamples, openFile, patch, refresh, rerun, review, rollback, selectFinding, selectNode, uploadFolder, uploadZip, useSample]);

  return { state, actions };
}
