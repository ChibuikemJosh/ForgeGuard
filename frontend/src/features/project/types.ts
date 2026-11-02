export interface ProjectReference { project_id: string; name: string; relative_path: string }
export interface ProjectFile { path: string; language: string | null; size_bytes: number; sha256: string | null; readable: boolean; error: string | null }
export interface ProjectManifest { project_id: string; name: string; relative_path: string; file_count: number; python_file_count: number; files: ProjectFile[]; ignored_directories: string[] }
export interface SampleProject { path: string; name: string; description: string }

export interface SourceReference { project_id: string | null; file_path: string; module: string | null; symbol: string; line_start: number | null; line_end: number | null; file_hash: string | null }
export interface SourceGraphNode { id: string; type: string; name: string; qualified_name: string | null; module: string | null; file_path: string | null; source: SourceReference | null; file_hash: string | null; metadata: Record<string, unknown> }
export interface SourceGraphEdge { id: string; source: string; target: string | null; type: string; status: string; observed: boolean; source_ref: SourceReference | null; evidence: string | null }
export interface SourceGraphSummary { total_nodes: number; total_edges: number; projects: number; modules: number; classes: number; functions: number; methods: number; routes: number; resolved_relationships: number; ambiguous_relationships: number; unresolved_relationships: number }
export interface SourceGraph { project_id: string; project_name: string | null; relative_path: string | null; nodes: SourceGraphNode[]; edges: SourceGraphEdge[]; errors: string[]; summary: SourceGraphSummary }

export interface SecurityRule { rule_id: string; title: string | null; invariant: string | null; name: string | null; description: string | null; category: string | null; severity: string; expected_property: string | null; concepts: string[]; indicators: string[]; guidance: string | null; examples: string[]; generated?: boolean }
export interface ProjectRuleSet { project_id: string; source: "sample" | "upload"; rule_origin: "preset" | "generated"; rules: SecurityRule[]; default_rule_id: string | null }

export interface SourceGraphNodeMatch { node_id: string; node_type: string; name: string; qualified_name: string | null; file_path: string | null; start_line: number | null; end_line: number | null; parent_node_id: string | null }
export interface EvidenceItem { evidence_id: string; evidence_type: string; description: string; file_path: string; source: SourceReference; excerpt: string | null; symbol_id: string | null; file_hash: string | null; observed: boolean; related_graph_nodes: string[]; node_matches: SourceGraphNodeMatch[]; status: string; validation_error: string | null }
export interface InvestigationStep { step_id: string; kind: "planning" | "model" | "tool" | "validation" | "mapping"; label: string; tool_name: string | null; status: "running" | "ok" | "failed" | "skipped"; message: string | null; started_at: string; duration_ms: number | null }
export interface InvestigationFinding { finding_id: string; rule_id: string; title: string; description: string; severity: string; confidence: number; status: string; affected_files: string[]; affected_symbols: string[]; related_graph_nodes: string[]; evidence: EvidenceItem[]; reasoning: string; recommended_remediation: string; verification_status: string }
export interface InvestigationResult { investigation_id: string; project_id: string; rule_id: string; status: string; findings: InvestigationFinding[]; errors: string[]; summary: string; truncated: boolean; steps: InvestigationStep[] }

export interface ProjectFixProposal { proposal_id: string; project_id: string; finding_id: string; file_path: string; expected_source_hash: string; original_content: string; proposed_content: string; unified_diff: string; explanation: string; review_status: string; application_status: string; rollback_available: boolean; reviewer: string | null; created_at: string; applied_at: string | null; error: string | null }
export interface FileContentResponse { project_id: string; path: string; content: string; sha256: string; language: string | null }
