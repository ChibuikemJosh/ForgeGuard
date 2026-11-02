/**
 * Minimal API client for the Forge FastAPI backend.
 *
 * The base URL is configurable through VITE_API_BASE_URL so the frontend can
 * target a locally running backend during development without hardcoding.
 */

export interface HealthResponse {
  status: string
  service: string
}

import type { Graph, GraphPreviewResponse, ValidationResult } from '../../features/graph/types'
import type { FileContentResponse, InvestigationResult, ProjectFixProposal, ProjectManifest, ProjectReference, ProjectRuleSet, SampleProject, SecurityRule as ProjectSecurityRule, SourceGraph } from '../../features/project/types'

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000'

function resolveApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL as string | undefined
  const trimmed = configured?.trim().replace(/\/+$/, '')
  return trimmed || DEFAULT_API_BASE_URL
}

const apiBaseUrl = resolveApiBaseUrl()

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${apiBaseUrl}${path}`

  let response: Response
  try {
    response = await fetch(url, {
      ...init,
      headers: {
        Accept: 'application/json',
        ...init?.headers,
      },
    })
  } catch (error) {
    // Re-throw aborts unchanged so callers can detect them reliably; wrap
    // genuine network failures with a message that explains what was attempted.
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error
    }
    throw new Error(`Request failed: could not reach the Forge backend at ${url}`, {
      cause: error,
    })
  }

  if (!response.ok) {
    let detail = ""
    try { const b = (await response.json()) as { detail?: string }; if (b?.detail) detail = `: ${b.detail}` } catch { /* non-JSON */ }
    throw new Error(`Request failed: ${response.status} ${response.statusText}${detail}`)
  }

  return (await response.json()) as T
}

export function apiUrl(path: string): string { return `${apiBaseUrl}${path}` }

const jsonInit = (method: string, body?: unknown, signal?: AbortSignal): RequestInit => ({ method, headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body), signal });
export async function listSamples(signal?: AbortSignal): Promise<SampleProject[]> { return requestJson<SampleProject[]>("/api/workspace/samples", { signal }); }
export async function openProject(path: string, name?: string, signal?: AbortSignal): Promise<ProjectReference> { return requestJson<ProjectReference>("/api/workspace/projects", jsonInit("POST", { path, name: name ?? null }, signal)); }
export async function uploadProjectZip(file: File, signal?: AbortSignal): Promise<ProjectReference> {
  return requestJson<ProjectReference>("/api/workspace/projects/upload", { method: "POST", headers: { "Content-Type": "application/zip", "x-file-name": file.name }, body: file, signal });
}
export async function getManifest(id: string, signal?: AbortSignal): Promise<ProjectManifest> { return requestJson<ProjectManifest>(`/api/workspace/projects/${encodeURIComponent(id)}/manifest`, { signal }); }
export async function getSourceGraph(id: string, signal?: AbortSignal): Promise<SourceGraph> { return requestJson<SourceGraph>(`/api/workspace/projects/${encodeURIComponent(id)}/source-graph`, { signal }); }
export async function getFileContent(id: string, path: string, signal?: AbortSignal): Promise<FileContentResponse> { return requestJson<FileContentResponse>(`/api/workspace/projects/${encodeURIComponent(id)}/files/content?path=${encodeURIComponent(path)}`, { signal }); }
export async function getProjectRules(id: string, signal?: AbortSignal): Promise<ProjectRuleSet> { const r = await requestJson<ProjectRuleSet>(`/api/workspace/projects/${encodeURIComponent(id)}/rules`, { signal }); return { ...r, rules: r.rules.map((x) => ({ ...x, generated: r.rule_origin === "generated" })) }; }
function investigationRule(rule: ProjectSecurityRule) {
  const { generated: _generated, ...backendRule } = rule;
  return backendRule;
}
export async function investigateProject(id: string, rule: ProjectSecurityRule, signal?: AbortSignal): Promise<InvestigationResult> { return requestJson<InvestigationResult>(`/api/workspace/projects/${encodeURIComponent(id)}/investigate`, jsonInit("POST", { rule: investigationRule(rule) }, signal)); }
export async function startInvestigation(id: string, rule: ProjectSecurityRule, signal?: AbortSignal): Promise<{ investigation_id: string; status: string }> { return requestJson<{ investigation_id: string; status: string }>(`/api/workspace/projects/${encodeURIComponent(id)}/investigations`, jsonInit("POST", { rule: investigationRule(rule) }, signal)); }
export async function getInvestigation(investigationId: string, signal?: AbortSignal): Promise<InvestigationResult> { return requestJson<InvestigationResult>(`/api/workspace/investigations/${encodeURIComponent(investigationId)}`, { signal }); }
export async function cancelInvestigation(investigationId: string, signal?: AbortSignal): Promise<InvestigationResult> { return requestJson<InvestigationResult>(`/api/workspace/investigations/${encodeURIComponent(investigationId)}/cancel`, jsonInit("POST", undefined, signal)); }
export async function listAppliedFixes(id: string, signal?: AbortSignal): Promise<ProjectFixProposal[]> { return requestJson<ProjectFixProposal[]>(`/api/workspace/projects/${encodeURIComponent(id)}/applied-fixes`, { signal }); }
async function downloadBlob(path: string, fallback: string, signal?: AbortSignal): Promise<{ blob: Blob; filename: string }> {
  const url = apiUrl(path);
  let response: Response;
  try { response = await fetch(url, { signal }); } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new Error(`Request failed: could not reach the Forge backend at ${url}`, { cause: error });
  }
  if (!response.ok) {
    let detail = "";
    try { const b = (await response.json()) as { detail?: string }; if (b?.detail) detail = `: ${b.detail}`; } catch { /* non-JSON */ }
    throw new Error(`Request failed: ${response.status} ${response.statusText}${detail}`);
  }
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="?([^";]+)"?/);
  return { blob: await response.blob(), filename: match?.[1] ?? fallback };
}
export async function downloadProjectPatch(id: string, signal?: AbortSignal): Promise<{ blob: Blob; filename: string }> { return downloadBlob(`/api/workspace/projects/${encodeURIComponent(id)}/changes.patch`, "forge-fixes.patch", signal); }
export async function downloadProjectZip(id: string, signal?: AbortSignal): Promise<{ blob: Blob; filename: string }> { return downloadBlob(`/api/workspace/projects/${encodeURIComponent(id)}/download`, "forge.zip", signal); }
export async function createFixProposal(id: string, findingId: string, instructions?: string, signal?: AbortSignal): Promise<ProjectFixProposal> { return requestJson<ProjectFixProposal>(`/api/workspace/projects/${encodeURIComponent(id)}/findings/${encodeURIComponent(findingId)}/fix-proposals`, jsonInit("POST", { instructions: instructions ?? null }, signal)); }
export async function getProjectFixProposal(pid: string, signal?: AbortSignal): Promise<ProjectFixProposal> { return requestJson<ProjectFixProposal>(`/api/workspace/fix-proposals/${encodeURIComponent(pid)}`, { signal }); }
export async function reviewProjectFixProposal(pid: string, body: { decision: "approved" | "rejected"; reviewer: string; actor: "human"; reason?: string }, signal?: AbortSignal): Promise<ProjectFixProposal> { return requestJson<ProjectFixProposal>(`/api/workspace/fix-proposals/${encodeURIComponent(pid)}/review`, jsonInit("POST", body, signal)); }
export async function applyProjectFixProposal(pid: string, signal?: AbortSignal): Promise<ProjectFixProposal> { return requestJson<ProjectFixProposal>(`/api/workspace/fix-proposals/${encodeURIComponent(pid)}/apply`, jsonInit("POST", undefined, signal)); }
export async function rollbackProjectFixProposal(pid: string, signal?: AbortSignal): Promise<ProjectFixProposal> { return requestJson<ProjectFixProposal>(`/api/workspace/fix-proposals/${encodeURIComponent(pid)}/rollback`, jsonInit("POST", undefined, signal)); }

export async function fetchBackendHealth(
  signal?: AbortSignal,
): Promise<HealthResponse> {
  return requestJson<HealthResponse>('/api/health', { signal })
}

export async function validateGraph(graph: Graph): Promise<ValidationResult> {
  return requestJson<ValidationResult>('/api/graph/validate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(graph),
  })
}

export async function previewGraph(graph: Graph): Promise<GraphPreviewResponse> {
  return requestJson<GraphPreviewResponse>('/api/graph/preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(graph),
  })
}
