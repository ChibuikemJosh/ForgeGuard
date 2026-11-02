interface Props { before: string; after: string; highlight: { start: number; end: number } | null; added?: Set<number> }

function Col({ title, subtitle, code, highlight, added }: { title: string; subtitle?: string; code: string; highlight: { start: number; end: number } | null; added?: Set<number> }) {
  const lines = code.split("\n");
  return (
    <div className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-md border border-line">
      <div className="border-b border-line bg-ide-bar px-2 py-1.5 font-mono text-[10px] text-zinc-300">{title}{subtitle ? <span className="block text-zinc-500">{subtitle}</span> : null}</div>
      <div className="workspace-scroll min-h-0 flex-1 overflow-auto p-2">
        {lines.map((l, i) => {
          const n = i + 1; const hl = highlight && n >= highlight.start && n <= highlight.end; const add = added?.has(n);
          return <div key={n} className={`flex font-mono text-[10.5px] leading-[1.55] ${add ? "bg-test-pass/15" : hl ? "bg-sev-critical/10" : ""}`}><span className="w-8 shrink-0 pr-2 text-right text-zinc-600">{n}</span><span className={`w-1 shrink-0 ${hl ? "bg-sev-critical" : add ? "bg-test-pass" : ""}`} /><pre className={`whitespace-pre ${add ? "text-test-pass" : "text-zinc-200"}`}>{l || " "}</pre></div>;
        })}
      </div>
    </div>
  );
}

export function SideBySideDiff({ before, after, highlight, added }: Props) {
  return (
    <div className="flex min-h-0 gap-2" aria-label="Side by side diff">
      <Col title="Original" code={before} highlight={highlight} />
      <Col title="Proposed" code={after} highlight={null} added={added} />
    </div>
  );
}
