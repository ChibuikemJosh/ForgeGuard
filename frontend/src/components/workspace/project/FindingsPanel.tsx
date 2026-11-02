import type { InvestigationFinding, InvestigationResult, SourceGraphNodeMatch } from "../../../features/project/types";

interface Props { result: InvestigationResult | null; selected: InvestigationFinding | null; onSelect: (f: InvestigationFinding) => void; onRunAgain?: () => void }

const BADGE: Record<string, string> = {
  potential: "bg-sev-warning/15 text-sev-warning",
  validated: "bg-test-pass/15 text-test-pass",
  inconclusive: "bg-panel text-zinc-400",
  failed: "bg-sev-critical/15 text-sev-critical",
  cancelled: "bg-panel text-zinc-500",
};

function breadcrumb(matches: SourceGraphNodeMatch[]): string {
  if (!matches.length) return "";
  const byId = new Map(matches.map((m) => [m.node_id, m]));
  const roots = matches.filter((m) => !m.parent_node_id || !byId.has(m.parent_node_id));
  const chain: SourceGraphNodeMatch[] = [];
  const visit = (m: SourceGraphNodeMatch) => { chain.push(m); const child = matches.find((x) => x.parent_node_id === m.node_id); if (child) visit(child); };
  if (roots[0]) visit(roots[0]);
  const ordered = chain.length ? chain : matches;
  const leaf = ordered[ordered.length - 1];
  const lines = leaf.start_line != null ? ` · L${leaf.start_line}${leaf.end_line && leaf.end_line !== leaf.start_line ? `–${leaf.end_line}` : ""}` : "";
  return ordered.map((m) => m.name).join(" › ") + lines;
}

export function FindingsPanel({ result, selected, onSelect, onRunAgain }: Props) {
  if (!result) return <section className="rounded-lg border border-line bg-panel p-3"><h3 className="font-mono text-[10px] uppercase text-zinc-400">Findings</h3><p className="mt-2 text-[11px] text-zinc-500">No investigation yet.</p></section>;
  return (
    <section className="rounded-lg border border-line bg-panel p-3" aria-label="Findings">
      <h3 className="font-mono text-[10px] uppercase text-zinc-400">Findings · status: {result.status}</h3>
      {result.status === "completed" ? <p className="mt-2 text-[11px] leading-relaxed text-zinc-300">{result.summary}</p> : null}
      {result.status === "inconclusive" && result.findings.length === 0 ? <p className="mt-2 text-[11px] leading-relaxed text-zinc-300">Muse did not identify any locations for this rule. This is not proof the rule holds; try a more specific rule or check truncation below.</p> : null}
      {result.status === "inconclusive" && result.findings.length > 0 ? <p className="mt-2 text-[11px] leading-relaxed text-zinc-300">Muse proposed locations, but none passed backend evidence validation.</p> : null}
      {result.status === "failed" ? <p className="mt-2 text-[11px] leading-relaxed text-sev-warning" role="alert">{result.errors[0] ?? result.summary}</p> : null}
      {result.status === "cancelled" ? (
        <div className="mt-2"><p className="text-[11px] text-zinc-300">Investigation was cancelled.</p>
          {onRunAgain ? <button type="button" onClick={onRunAgain} className="mt-2 rounded bg-ember px-3 py-1.5 text-[11px] font-semibold text-white focus-visible:outline-2 focus-visible:outline-ide-blue">Run again</button> : null}
        </div>
      ) : null}
      {result.truncated ? <p className="mt-2 rounded bg-sev-warning/10 px-2 py-1 text-[11px] text-sev-warning">Not all Python files were sent to the model. Results may be incomplete.</p> : null}
      <div className="mt-3 flex flex-col gap-2">
        {result.findings.length === 0 ? <p className="text-[11px] text-zinc-500">Backend returned no findings.</p> : result.findings.map((f) => (
          <article key={f.finding_id} className={`rounded-md border p-2 ${selected?.finding_id === f.finding_id ? "border-ember bg-panel-2" : "border-line bg-panel-2/60"}`}>
            <button type="button" onClick={() => onSelect(f)} aria-pressed={selected?.finding_id === f.finding_id}
              className="w-full text-left focus-visible:outline-2 focus-visible:outline-ide-blue">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-[12px] font-semibold text-zinc-100">{f.title}</span>
                <span className={`rounded px-1.5 py-0.5 font-mono text-[9px] ${BADGE[f.status] ?? BADGE.inconclusive}`}>{f.status}</span>
                <span className="rounded bg-panel px-1.5 py-0.5 font-mono text-[9px] text-zinc-400">{f.severity}</span>
                <span className="font-mono text-[9px] text-zinc-500">confidence {f.confidence}</span>
              </div>
              <p className="mt-1 text-[11px] leading-relaxed text-zinc-400">{f.description}</p>
              <p className="mt-1 font-mono text-[9px] text-zinc-500">{f.affected_files.join(", ") || "no affected files"}</p>
            </button>
            <div className="mt-2 flex flex-col gap-1">
              {f.evidence.map((e) => (
                <div key={e.evidence_id} className="rounded bg-panel px-2 py-1 font-mono text-[9px] leading-relaxed text-zinc-400">
                  <span className="text-zinc-200">{e.file_path}:{e.source.line_start ?? "?"}</span> · validation: {e.status}
                  {e.validation_error ? <span className="text-sev-warning"> — {e.validation_error}</span> : null}
                  {e.node_matches?.length ? <span className="block text-zinc-300">{breadcrumb(e.node_matches)}</span> : null}
                  {e.excerpt ? <pre className="mt-0.5 whitespace-pre-wrap text-zinc-300">{e.excerpt}</pre> : null}
                </div>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
