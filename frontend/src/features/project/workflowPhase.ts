import type {
  InvestigationResult,
  ProjectFixProposal,
  ProjectReference,
  SourceGraph,
} from "./types";

export type ProjectPhase =
  | "idle"
  | "project_selected"
  | "analyzing"
  | "graph_ready"
  | "investigating"
  | "findings_ready"
  | "proposing_fix"
  | "proposal_ready"
  | "approved"
  | "applying"
  | "applied"
  | "error";

/** The slice of workflow state that determines where the user stands. */
export interface PhaseSnapshot {
  project: ProjectReference | null;
  graph: SourceGraph | null;
  investigation: InvestigationResult | null;
  proposal: ProjectFixProposal | null;
}

/**
 * Derive the workspace phase from retained workflow data instead of trusting
 * the last transition. Errors, cancellations and dismissals recover here, so a
 * side-effect failure (a download, a re-run, a cancel) can never strand an
 * in-flight approval back in "idle" or "project_selected".
 */
export function recoverPhase(s: PhaseSnapshot): ProjectPhase {
  if (!s.project) return "idle";
  if (s.proposal?.application_status === "applied") return "applied";
  if (s.proposal?.review_status === "approved") return "approved";
  if (s.proposal) return "proposal_ready";
  if (s.investigation) return "findings_ready";
  if (s.graph) return "graph_ready";
  return "project_selected";
}
