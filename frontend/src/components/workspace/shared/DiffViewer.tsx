export function DiffViewer({ diff }: { diff: string | null }) {
  if (!diff) return <p className="font-mono text-[11px] text-zinc-500">No diff available.</p>;
  return (
    <div className="overflow-hidden rounded-md border border-line font-mono text-[10.5px] leading-relaxed" aria-label="Unified diff">
      {diff.split("\n").map((line, i) => {
        const isAdd = line.startsWith("+") && !line.startsWith("+++");
        const isDel = line.startsWith("-") && !line.startsWith("---");
        const isHunk = line.startsWith("@@");
        return (
          <div key={i} className={`flex ${isAdd ? "bg-test-pass/10" : isDel ? "bg-sev-critical/10" : isHunk ? "bg-ide-active/60" : ""}`}>
            <span className={`w-6 shrink-0 text-center ${isAdd ? "text-test-pass" : isDel ? "text-sev-critical" : "text-zinc-600"}`}>{isAdd ? "+" : isDel ? "−" : " "}</span>
            <pre className={`whitespace-pre-wrap ${isAdd ? "text-test-pass" : isDel ? "text-sev-critical" : isHunk ? "text-ember-bright" : "text-zinc-300"}`}>{line.slice(isAdd || isDel ? 1 : 0) || " "}</pre>
          </div>
        );
      })}
    </div>
  );
}
