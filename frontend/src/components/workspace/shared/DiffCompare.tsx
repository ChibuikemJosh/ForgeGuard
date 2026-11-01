import { useEffect } from "react";
import { motion } from "motion/react";
import { DiffViewer } from "./DiffViewer";
interface Props { open: boolean; onClose: () => void; before: string; after: string; diff: string | null; highlight: { start: number; end: number } | null }
function Col({ title, code, highlight, added }: { title: string; code: string; highlight: { start: number; end: number } | null; added?: Set<number> }) {
  const lines = code.split("\n");
  return (
    <div className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-md border border-line">
      <div className="border-b border-line bg-ide-bar px-2 py-1.5 font-mono text-[10px] text-zinc-300">{title}</div>
      <div className="workspace-scroll min-h-0 flex-1 overflow-auto p-2">
        {lines.map((l, i) => {
          const n = i + 1; const hl = highlight && n >= highlight.start && n <= highlight.end; const add = added?.has(n);
          return <div key={n} className={`flex font-mono text-[10.5px] leading-[1.55] ${add ? "bg-test-pass/15" : hl ? "bg-sev-critical/10" : ""}`}><span className="w-8 shrink-0 pr-2 text-right text-zinc-600">{n}</span><span className={`w-1 shrink-0 ${hl ? "bg-sev-critical" : add ? "bg-test-pass" : ""}`} /><pre className={`whitespace-pre ${add ? "text-test-pass" : "text-zinc-200"}`}>{l || " "}</pre></div>;
        })}
      </div>
    </div>
  );
}
export function DiffCompare({ open, onClose, before, after, diff, highlight }: Props) {
  useEffect(() => { if (!open) return; const h = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); }; window.addEventListener("keydown", h); return () => window.removeEventListener("keydown", h); }, [open, onClose]);
  if (!open) return null;
  // compute added from after vs before crudely via diff handled by parent prop reuse: use DiffViewer below too
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4" role="dialog" aria-modal="true" aria-label="Compare original and AI proposed fix">
      <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} className="flex max-h-[92vh] w-full max-w-6xl flex-col rounded-lg border border-line bg-panel p-3 font-ui">
        <div className="flex items-center gap-2 pb-2">
          <h2 className="text-[13px] font-semibold text-zinc-100">Compare — original vs proposed fix</h2>
          <span className="font-mono text-[9px] text-zinc-500">from approved unified_diff</span>
          <button type="button" onClick={onClose} className="ml-auto rounded px-2 py-1 text-zinc-400 hover:bg-ide-hover focus-visible:outline-2 focus-visible:outline-ide-blue" aria-label="Close compare">✕ Esc</button>
        </div>
        <div className="flex min-h-0 flex-1 gap-2">
          <Col title="Original (before)" code={before} highlight={highlight} />
          <Col title="Proposed fix (after — from approved diff)" code={after} highlight={null} />
        </div>
        <details className="mt-2"><summary className="cursor-pointer font-mono text-[10px] text-ember-bright">Unified diff</summary><div className="mt-1 max-h-48 overflow-auto"><DiffViewer diff={diff} /></div></details>
      </motion.div>
    </div>
  );
}
