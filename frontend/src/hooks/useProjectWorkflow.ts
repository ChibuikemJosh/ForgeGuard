import { useCallback, useEffect, useMemo, useReducer, useRef } from "react";
import { toast } from "sonner";
import * as api from "../services/api/client";
import { zipFolder } from "../features/project/zipFolder";
import type { FileContentResponse, InvestigationFinding, InvestigationResult, ProjectFixProposal, ProjectManifest, ProjectReference, SampleProject, SecurityRule, SourceGraph } from "../features/project/types";

export type ProjectPhase = "idle" | "project_selected" | "analyzing" | "graph_ready" | "investigating" | "findings_ready" | "proposing_fix" | "proposal_ready" | "approved" | "applying" | "applied" | "error";

export interface ProjectState {
  phase: ProjectPhase; busy: boolean; error: string | null; retryPhase: ProjectPhase;
  backendOk: boolean | null; samples: SampleProject[]; project: ProjectReference | null;
  manifest: ProjectManifest | null; graph: SourceGraph | null; rules: SecurityRule[];
  rule: SecurityRule | null; ruleOrigin: "preset" | "generated" | null; rulesLoading: boolean;
  investigation: InvestigationResult | null;
  selectedFinding: InvestigationFinding | null; selectedNodeId: string | null;
  selectedFile: string | null; highlightLine: number | null; fileContent: FileContentResponse | null;
  proposal: ProjectFixProposal | null; appliedFixes: ProjectFixProposal[];
  /** Backend summary word-for-word from an investigation re-run after apply. */
  verifiedSummary: string | null;
}
const initial: ProjectState = { phase: "idle", busy: false, error: null, retryPhase: "idle", backendOk: null, samples: [], project: null, manifest: null, graph: null, rules: [], rule: null, ruleOrigin: null, rulesLoading: false, investigation: null, selectedFinding: null, selectedNodeId: null, selectedFile: null, highlightLine: null, fileContent: null, proposal: null, appliedFixes: [], verifiedSummary: null };
type Action = { type: "patch"; patch: Partial<ProjectState> };
function reducer(s: ProjectState, a: Action): ProjectState {
  return { ...s, ...a.patch };
}

export function useProjectWorkflow() {
  const [state, dispatch] = useReducer(reducer, initial);
  const controllers = useRef(new Set<AbortController>());
  const investigationIdRef = useRef<string | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stopPolling = useCallback(() => { if (pollTimerRef.current) { clearTimeout(pollTimerRef.current); pollTimerRef.current = null; } }, []);
  const stateRef = useRef(state);
  useEffect(() => { stateRef.current = state; }, [state]);
  const patch = useCallback((p: Partial<ProjectState>) => dispatch({ type: "patch", patch: p }), []);
  const cancel = useCallback(() => {
    const invId = investigationIdRef.current;
    investigationIdRef.current = null;
    stopPolling();
    if (invId && stateRef.current.phase === "investigating") {
      void (async () => {
        try {
          const r = await api.cancelInvestigation(invId);
          patch({ busy: false, investigation: r, phase: "findings_ready" });
          toast.success(r.summary);
        } catch { /* fall through to abort */ }
        controllers.current.forEach((c) => c.abort()); controllers.current.clear();
      })();
      return;
    }
    controllers.current.forEach((c) => c.abort());
    controllers.current.clear();
    patch({ busy: false, phase: stateRef.current.project ? "project_selected" : "idle" });
  }, [patch, stopPolling]);

  const call = useCallback(async <T,>(fn: (s: AbortSignal) => Promise<T>): Promise<T> => {
    const c = new AbortController();
    controllers.current.add(c);
    try { return await fn(c.signal); }
    finally { controllers.current.delete(c); }
  }, []);

  const fail = useCallback((e: unknown, retry: ProjectPhase) => {
    if (e instanceof DOMException && e.name === "AbortError") { patch({ busy: false }); return; }
    const msg = e instanceof Error ? e.message : "Request failed";
    if (msg.includes("404") && msg.includes("Unknown")) {
      const friendly = "The backend restarted and lost this session's investigation. Run the investigation again (or re-upload the project folder).";
      const recoverPhase: ProjectPhase = stateRef.current.project && stateRef.current.graph ? "graph_ready" : "idle";
      patch({ busy: false, error: friendly, phase: recoverPhase, retryPhase: recoverPhase }); toast.error(friendly); return;
    }
    patch({ busy: false, error: msg, phase: "error", retryPhase: retry }); toast.error(msg);
  }, [patch]);

  const refreshApplied = useCallback(async (pid?: string) => {
    const id = pid ?? stateRef.current.project?.project_id; if (!id) return;
    try { const fixes = await call((s) => api.listAppliedFixes(id, s)); patch({ appliedFixes: fixes }); } catch { /* downloads surface errors separately */ }
  }, [call, patch]);

  const downloadWith = useCallback(async (kind: "patch" | "zip") => {
    const pid = stateRef.current.project?.project_id; if (!pid) return;
    try {
      const { blob, filename } = kind === "patch"
        ? await call((s) => api.downloadProjectPatch(pid, s))
        : await call((s) => api.downloadProjectZip(pid, s));
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = filename; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) { fail(e, stateRef.current.phase); }
  }, [call, fail]);
  const downloadPatch = useCallback(() => downloadWith("patch"), [downloadWith]);
  const downloadZip = useCallback(() => downloadWith("zip"), [downloadWith]);

  const checkHealth = useCallback(async () => {
    try { await call((s) => api.fetchBackendHealth(s)); patch({ backendOk: true }); }
    catch { patch({ backendOk: false }); }
  }, [call, patch]);

  const loadSamples = useCallback(async () => {
    try {
      const samples = await call((s) => api.listSamples(s));
      patch({ samples });
    } catch (e) { fail(e, "idle"); }
  }, [call, fail, patch]);

  const selectProjectRef = useCallback(async (ref: ProjectReference) => {
    patch({ project: ref, phase: "analyzing", busy: true, error: null, graph: null, investigation: null, proposal: null, selectedFinding: null, selectedFile: null, fileContent: null, verifiedSummary: null, manifest: null, rules: [], rule: null, ruleOrigin: null });
    try {
      const m = await call((s) => api.getManifest(ref.project_id, s));
      patch({ manifest: m });
      const g = await call((s) => api.getSourceGraph(ref.project_id, s));
      patch({ busy: false, graph: g, phase: "graph_ready" });
      patch({ rulesLoading: true });
      try {
        const ruleSet = await call((s) => api.getProjectRules(ref.project_id, s));
        patch({ rules: ruleSet.rules, ruleOrigin: ruleSet.rule_origin, rulesLoading: false, rule: ruleSet.rules.find((r) => r.rule_id === ruleSet.default_rule_id) ?? null });
      } catch (e) {
        patch({ rules: [], rulesLoading: false });
        if (!(e instanceof DOMException && e.name === "AbortError")) toast.error(e instanceof Error ? e.message : "Request failed");
      }
      void refreshApplied(ref.project_id);
    } catch (e) { fail(e, "idle"); }
  }, [call, fail, patch, refreshApplied]);

  const changeProject = useCallback(() => {
    stopPolling();
    controllers.current.forEach((c) => c.abort()); controllers.current.clear();
    stopPolling(); investigationIdRef.current = null;
    patch({ project: null, manifest: null, graph: null, investigation: null, proposal: null, appliedFixes: [], selectedFinding: null, selectedNodeId: null, selectedFile: null, fileContent: null, highlightLine: null, error: null, busy: false, phase: "idle", verifiedSummary: null, rules: [], rule: null, ruleOrigin: null, rulesLoading: false });
  }, [patch, stopPolling]);

  const refresh = useCallback(async () => {
    const pid = stateRef.current.project?.project_id; if (!pid) return;
    patch({ busy: true, error: null, phase: "analyzing" });
    try {
      const m = await call((s) => api.getManifest(pid, s));
      const g = await call((s) => api.getSourceGraph(pid, s));
      patch({ busy: false, manifest: m, graph: g, phase: "graph_ready" });
    } catch (e) { fail(e, "project_selected"); }
  }, [call, fail, patch]);

  const useSample = useCallback(async (sample: SampleProject) => {
    patch({ busy: true, error: null });
    try { const ref = await call((s) => api.openProject(sample.path, sample.name, s)); patch({ busy: false }); await selectProjectRef(ref); }
    catch (e) { fail(e, "idle"); }
  }, [call, fail, patch, selectProjectRef]);

  const uploadFolder = useCallback(async (files: File[]) => {
    patch({ busy: true, error: null });
    try {
      const { zip, fileCount, skippedCount } = await zipFolder(files);
      const ref = await call((s) => api.uploadProjectZip(zip, s));
      patch({ busy: false }); await selectProjectRef(ref);
      toast.success(`Uploaded ${zip.name.replace(/\.zip$/, "")} (${fileCount} files${skippedCount ? `, ${skippedCount} skipped` : ""})`);
    } catch (e) { fail(e, "idle"); }
  }, [call, fail, patch, selectProjectRef]);

  const analyze = useCallback(async () => {
    const pid = stateRef.current.project?.project_id; if (!pid) return;
    patch({ busy: true, error: null, phase: "analyzing" });
    try { const g = await call((s) => api.getSourceGraph(pid, s)); patch({ busy: false, graph: g, phase: "graph_ready" }); }
    catch (e) { fail(e, "project_selected"); }
  }, [call, fail, patch]);

  const openFile = useCallback(async (path: string, line?: number | null) => {
    const pid = stateRef.current.project?.project_id; if (!pid) return;
    patch({ selectedFile: path, highlightLine: line ?? null });
    try { const c = await call((s) => api.getFileContent(pid, path, s)); patch({ fileContent: c }); }
    catch (e) { fail(e, stateRef.current.phase); }
  }, [call, fail, patch]);

  const investigate = useCallback(async () => {
    const st = stateRef.current; const pid = st.project?.project_id; const rule = st.rule; if (!pid || !rule) return;
    const wasApplied = st.proposal?.application_status === "applied";
    patch({ busy: true, error: null, phase: "investigating", ...(wasApplied ? {} : { proposal: null, selectedFinding: null }) });
    try {
      const started = await call((s) => api.startInvestigation(pid, rule, s));
      investigationIdRef.current = started.investigation_id;
      const deadline = Date.now() + 10 * 60 * 1000;
      // Poll live progress until the job leaves "running".
      for (;;) {
        if (Date.now() > deadline) { patch({ busy: false, error: "Investigation is taking longer than expected" }); toast.error("Investigation is taking longer than expected"); return; }
        await new Promise((resolve) => { pollTimerRef.current = setTimeout(resolve, 1500); });
        if (!investigationIdRef.current) return; // cancelled / project changed
        const r = await call((s) => api.getInvestigation(started.investigation_id, s));
        patch({ investigation: r });
        if (r.status !== "running") {
          investigationIdRef.current = null;
          patch({ busy: false, investigation: r, phase: "findings_ready", ...(wasApplied ? { verifiedSummary: r.summary } : {}) });
          if (r.status === "failed") toast.error(r.errors[0] ?? r.summary);
          else toast.success(r.summary);
          return;
        }
      }
    } catch (e) { investigationIdRef.current = null; fail(e, "graph_ready"); }
  }, [call, fail, patch]);

  const selectFinding = useCallback((f: InvestigationFinding | null) => {
    const narrowest = f?.evidence.flatMap((e) => e.node_matches ?? []).find((m) => ["route", "method", "function"].includes(m.node_type))
      ?? f?.evidence.flatMap((e) => e.node_matches ?? []).find((m) => m.node_type === "class")
      ?? f?.evidence.flatMap((e) => e.node_matches ?? []).find((m) => m.node_type === "module");
    patch({ selectedFinding: f, selectedNodeId: narrowest?.node_id ?? f?.related_graph_nodes[0] ?? null });
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
    try { const p = await call((s) => api.createFixProposal(pid, f.finding_id, instructions || undefined, s)); patch({ busy: false, proposal: p, phase: "proposal_ready" }); }
    catch (e) { fail(e, "findings_ready"); }
  }, [call, fail, patch]);

  const review = useCallback(async (decision: "approved" | "rejected", reviewer: string) => {
    const p = stateRef.current.proposal; if (!p) return;
    patch({ busy: true, error: null });
    try { const r = await call((s) => api.reviewProjectFixProposal(p.proposal_id, { decision, reviewer, actor: "human" }, s)); patch({ busy: false, proposal: r, phase: decision === "approved" ? "approved" : "proposal_ready" }); }
    catch (e) { fail(e, "proposal_ready"); }
  }, [call, fail, patch]);

  const apply = useCallback(async () => {
    const p = stateRef.current.proposal; if (!p) return;
    patch({ busy: true, error: null, phase: "applying" });
    try { const r = await call((s) => api.applyProjectFixProposal(p.proposal_id, s)); patch({ busy: false, proposal: r, phase: "applied" }); void refreshApplied(); if (stateRef.current.selectedFile) void openFile(stateRef.current.selectedFile, stateRef.current.highlightLine); toast.success("Fix applied"); }
    catch (e) { fail(e, "approved"); }
  }, [call, fail, openFile, patch, refreshApplied]);

  const rollback = useCallback(async () => {
    const p = stateRef.current.proposal; if (!p) return;
    patch({ busy: true, error: null });
    try { const r = await call((s) => api.rollbackProjectFixProposal(p.proposal_id, s)); patch({ busy: false, proposal: r, phase: "approved", verifiedSummary: null }); void refreshApplied(); if (stateRef.current.selectedFile) void openFile(stateRef.current.selectedFile, stateRef.current.highlightLine); toast.success("Rolled back"); }
    catch (e) { fail(e, "applied"); }
  }, [call, fail, openFile, patch, refreshApplied]);

  const rerun = useCallback(async () => { await analyze(); await investigate(); }, [analyze, investigate]);

  const actions = useMemo(() => ({
    checkHealth, loadSamples, useSample, uploadFolder, analyze, investigate, rerun, changeProject, refresh,
    setRule: (r: SecurityRule | null) => patch({ rule: r }),
    selectFinding, selectNode, openFile, generateFix, review, apply, rollback, cancel, downloadPatch, downloadZip, refreshApplied,
    clearError: () => patch({ error: null, phase: stateRef.current.retryPhase }),
  }), [analyze, apply, cancel, changeProject, checkHealth, downloadPatch, downloadZip, generateFix, investigate, loadSamples, openFile, patch, refresh, refreshApplied, rerun, review, rollback, selectFinding, selectNode, uploadFolder, useSample]);

  return { state, actions };
}
