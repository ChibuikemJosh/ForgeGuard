import type { InvestigationFinding, InvestigationResult } from "../../../features/project/types";

interface Props { result: InvestigationResult | null; selected: InvestigationFinding | null; onSelect: (f: InvestigationFinding) => void }

export function FindingsPanel({ result, selected, onSelect }: Props) {
  if (!result) return <section className="rounded-lg border border-line bg-panel p-3"><h3 className="font-mono text-[10px] uppercase text-zinc-400">Findings</h3><p className="mt-2 text-[11px] text-zinc-500">No investigation yet.</p></section>;
  return (
    <section className="rounded-lg border border-line bg-panel p-3" aria-label="Findings">
      <h3 className="font-mono text-[10px] uppercase text-zinc-400">Findings · status: {result.status}</h3>
      <p className="mt-2 text-[11px] leading-relaxed text-zinc-300">{result.summary}</p>
      {result.errors.map((e) => <p key={e} className="mt-1 rounded bg-sev-warning/10 px-2 py-1 font-mono text-[10px] text-sev-warning" role="alert">{e}</p>)}
      <div className="mt-3 flex flex-col gap-2">
        {result.findings.length === 0 ? <p className="text-[11px] text-zinc-500">Backend returned no findings.</p> : result.findings.map((f) => (
          <button key={f.finding_id} type="button" onClick={() => onSelect(f)} aria-pressed={selected?.finding_id === f.finding_id}
            className={`rounded-md border p-2 text-left focus-visible:outline-2 focus-visible:outline-ide-blue ${selected?.finding_id === f.finding_id ? "border-ember bg-panel-2" : "border-line bg-panel-2/60 hover:bg-panel-2"}`}>
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[12px] font-semibold text-zinc-100">{f.title}</span>
              <span className="rounded bg-sev-warning/15 px-1.5 py-0.5 font-mono text-[9px] text-sev-warning">{f.status}</span>
              <span className="rounded bg-panel px-1.5 py-0.5 font-mono text-[9px] text-zinc-400">{f.severity}</span>
              <span className="font-mono text-[9px] text-zinc-500">confidence {f.confidence}</span>
            </div>
            <p className="mt-1 text-[11px] leading-relaxed text-zinc-400">{f.description}</p>
            <p className="mt-1 font-mono text-[9px] text-zinc-500">{f.affected_files.join(", ") || "no affected files"}</p>
            <div className="mt-2 flex flex-col gap-1">
              {f.evidence.map((e) => (
                <div key={e.evidence_id} className="rounded bg-panel px-2 py-1 font-mono text-[9px] leading-relaxed text-zinc-400">
                  <span className="text-zinc-200">{e.file_path}:{e.source.line_start ?? "?"}</span> · validation: {e.status}
                  {e.validation_error ? <span className="text-sev-warning"> — {e.validation_error}</span> : null}
                  {e.excerpt ? <pre className="mt-0.5 whitespace-pre-wrap text-zinc-300">{e.excerpt}</pre> : null}
                </div>
              ))}
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}
