import type { InvestigationResult, ProjectManifest, SourceGraph } from "./types";
import type { SkippedFile } from "./zipFolder";

export interface Problem {
  id: string;
  kind: "parse" | "unreadable" | "skipped" | "unresolved" | "truncated" | "investigation";
  message: string;
  filePath?: string;
}

export interface ProblemsState {
  graph: SourceGraph | null;
  manifest: ProjectManifest | null;
  investigation: InvestigationResult | null;
  uploadSkipped: SkippedFile[];
}

/** Pull a file path out of a backend error message, if one is present. */
function extractFilePath(message: string): string | undefined {
  const m = message.match(/([^\s:'"]+\.(?:py|pyi|txt|md|toml|cfg|ini|json|ya?ml))(?:[:\s]|$)/);
  return m?.[1];
}

export function buildProblems(state: ProblemsState): Problem[] {
  const out: Problem[] = [];
  state.graph?.errors.forEach((msg, i) => {
    out.push({ id: `parse-${i}`, kind: "parse", message: msg, filePath: extractFilePath(msg) });
  });
  state.manifest?.files.filter((f) => !f.readable).forEach((f, i) => {
    out.push({ id: `unreadable-${i}-${f.path}`, kind: "unreadable", message: f.error ?? f.path, filePath: f.path });
  });
  state.uploadSkipped.forEach((s, i) => {
    out.push({ id: `skipped-${i}-${s.path}`, kind: "skipped", message: `${s.path} — ${s.reason}`, filePath: undefined });
  });
  if (state.graph) {
    const n = state.graph.summary.unresolved_relationships + state.graph.summary.ambiguous_relationships;
    if (n > 0) out.push({ id: "unresolved", kind: "unresolved", message: `${n} calls couldn't be resolved; some graph edges are missing` });
  }
  if (state.investigation?.truncated) {
    out.push({ id: "truncated", kind: "truncated", message: "Not all Python files were sent to the model. Results may be incomplete." });
  }
  state.investigation?.errors.forEach((msg, i) => {
    out.push({ id: `investigation-${i}`, kind: "investigation", message: msg, filePath: extractFilePath(msg) });
  });
  return out;
}
