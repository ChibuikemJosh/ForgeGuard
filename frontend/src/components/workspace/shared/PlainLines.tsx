export function PlainLines({ lines, highlight, added }: { lines: string[]; highlight: { start: number; end: number } | null; added?: Set<number> }) {
  return <>{lines.map((l, i) => { const n = i + 1; const hl = highlight && n >= highlight.start && n <= highlight.end; const add = added?.has(n); return (
    <div key={n} data-line={n} className={`flex font-mono text-[11px] leading-[1.6] ${add ? "bg-test-pass/12" : hl ? "bg-sev-critical/10" : ""}`}><span className="w-10 shrink-0 select-none pr-2 text-right text-zinc-600">{n}</span><span className={`w-1 shrink-0 ${hl ? "bg-sev-critical" : add ? "bg-test-pass" : ""}`} aria-hidden /><pre className={`whitespace-pre pr-4 ${add ? "text-test-pass" : "text-zinc-200"}`}>{l || " "}</pre></div>); })}</>;
}
