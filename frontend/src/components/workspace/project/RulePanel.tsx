import { useState } from "react";
import type { SecurityRule } from "../../../features/project/types";
interface Props { rules: SecurityRule[]; rule: SecurityRule | null; onSelect: (r: SecurityRule) => void; busy: boolean; canInvestigate: boolean; onInvestigate: () => void; onCancel: () => void; investigating: boolean; pythonCount?: number | null }

const blank = (id: string): SecurityRule => ({ rule_id: id, title: "", invariant: "", name: null, description: null, category: null, severity: "high", expected_property: null, concepts: [], indicators: [], guidance: null, examples: [] });

export function RulePanel({ rules, rule, onSelect, busy, canInvestigate, onInvestigate, onCancel, investigating }: Props) {
  const [custom, setCustom] = useState({ title: "", invariant: "", description: "", indicators: "" });
  const useCustom = () => {
    if (!custom.title.trim() || !custom.invariant.trim()) return;
    const r = blank(`custom-${Date.now()}`);
    onSelect({ ...r, title: custom.title, invariant: custom.invariant, description: custom.description || null, indicators: custom.indicators.split(",").map((x) => x.trim()).filter(Boolean) });
  };
  const input = "w-full rounded border border-line bg-panel-2 px-2 py-1.5 text-[11px] text-zinc-100 focus-visible:outline-2 focus-visible:outline-ide-blue";
  return (
    <section className="rounded-lg border border-line bg-panel p-3" aria-label="Security rule">
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-mono text-[10px] uppercase tracking-wide text-zinc-400">Security rule</h3>
        <div className="group relative">
          <button type="button" aria-label="What are rules and how do they work?" className="grid size-5 place-items-center rounded-full border border-line font-mono text-[10px] text-zinc-400 hover:border-zinc-500 hover:text-zinc-100 focus-visible:outline-2 focus-visible:outline-ide-blue">?</button>
          <div role="tooltip" className="pointer-events-none absolute right-0 top-6 z-20 w-64 rounded-md border border-line bg-panel-2 p-3 text-[11px] leading-relaxed text-zinc-300 opacity-0 shadow-xl transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
            <p className="font-semibold text-zinc-100">What is a rule?</p>
            <p className="mt-1">A rule is a security property that should always hold in your project — for example, “users may only access their own orders”. Forge sends the selected rule, plus relevant code from your project, to the AI investigator.</p>
            <p className="mt-1">The investigator looks for places that may break the rule, maps them to the graph, and returns findings with evidence. Preset rules are fixed examples. Rules labelled “Generated for your project” are derived from your own routes and resource IDs. You can also write a custom rule below.</p>
            <p className="mt-1 text-zinc-400">Pick a rule, then choose “Run AI investigation”. Nothing is changed until you review and apply a fix in the Changes tab.</p>
          </div>
        </div>
      </div>
      <label className="mt-2 block text-[11px] text-zinc-300">Preset
        <select className={`${input} mt-1`} value={rule?.rule_id ?? ""} onChange={(e) => { const r = rules.find((x) => x.rule_id === e.target.value); if (r) onSelect(r); }}>
          <option value="" disabled>Choose a rule…</option>
          {rules.map((r) => <option key={r.rule_id} value={r.rule_id}>{r.generated ? "Generated for your project · " : ""}{r.title ?? r.rule_id}</option>)}
        </select>
      </label>
      {rule ? <div className="mt-2 rounded-md bg-panel-2 p-2 text-[11px] leading-relaxed text-zinc-300"><p>{rule.invariant}</p>{rule.description ? <p className="mt-1 text-zinc-400">{rule.description}</p> : null}<p className="mt-1 font-mono text-[9px] text-zinc-500">{rule.rule_id} · severity {rule.severity}{rule.generated ? " · generated for your project" : ""}</p></div> : null}
      <details className="mt-3">
        <summary className="cursor-pointer text-[11px] text-zinc-300">Custom rule</summary>
        <div className="mt-2 flex flex-col gap-2">
          <input className={input} placeholder="Title" value={custom.title} onChange={(e) => setCustom({ ...custom, title: e.target.value })} />
          <textarea className={input} placeholder="Invariant (what must always hold)" rows={3} value={custom.invariant} onChange={(e) => setCustom({ ...custom, invariant: e.target.value })} />
          <input className={input} placeholder="Description (optional)" value={custom.description} onChange={(e) => setCustom({ ...custom, description: e.target.value })} />
          <input className={input} placeholder="Indicators, comma separated (optional)" value={custom.indicators} onChange={(e) => setCustom({ ...custom, indicators: e.target.value })} />
          <button type="button" onClick={useCustom} disabled={!custom.title.trim() || !custom.invariant.trim()} className="rounded border border-line px-2 py-1.5 text-[11px] text-zinc-200 hover:bg-ide-hover disabled:opacity-40">Use custom rule</button>
        </div>
      </details>
      {investigating ? (
        <div className="mt-3">
        <button type="button" onClick={onCancel} className="mt-2 w-full rounded border border-line px-3 py-2 text-[12px] text-zinc-200 hover:bg-ide-hover focus-visible:outline-2 focus-visible:outline-ide-blue">Cancel</button></div>
      ) : (
        <button type="button" disabled={!canInvestigate || busy} onClick={onInvestigate} className="mt-3 w-full rounded bg-ember px-3 py-2 text-[12px] font-semibold text-white hover:bg-ember-soft disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-ide-blue">Run AI investigation</button>
      )}
    </section>
  );
}
