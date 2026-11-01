import { useEffect, useState } from "react";
import { PlainLines } from "./PlainLines";
interface Token { content: string; color?: string }
export default function ShikiLines({ code, highlight, added }: { code: string; highlight: { start: number; end: number } | null; added?: Set<number> }) {
  const [tokenLines, setTokenLines] = useState<Token[][] | null>(null);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { createHighlighterCore } = await import("shiki/core");
        const { createJavaScriptRegexEngine } = await import("shiki/engine/javascript");
        const pythonMod = await import("shiki/dist/langs/python.mjs");
        const themeMod = await import("shiki/dist/themes/github-dark.mjs");
        const python = pythonMod.default ?? pythonMod;
        const theme = themeMod.default ?? themeMod;
        const hl = await createHighlighterCore({ themes: [theme], langs: [python], engine: createJavaScriptRegexEngine() });
        const tokens = hl.codeToTokens(code, { lang: "python", theme: "github-dark" });
        if (!cancelled) setTokenLines(tokens.tokens as unknown as Token[][]);
      } catch { if (!cancelled) setTokenLines(null); }
    })();
    return () => { cancelled = true; };
  }, [code]);
  if (!tokenLines) return <PlainLines lines={code.split("\n")} highlight={highlight} added={added} />;
  return <>{tokenLines.map((toks, i) => { const n = i + 1; const hl = highlight && n >= highlight.start && n <= highlight.end; const add = added?.has(n); return (
    <div key={n} data-line={n} className={`flex font-mono text-[11px] leading-[1.6] ${add ? "bg-test-pass/10" : hl ? "bg-sev-critical/10" : ""}`}><span className="w-10 shrink-0 select-none pr-2 text-right text-zinc-600">{n}</span><span className={`w-1 shrink-0 ${hl ? "bg-sev-critical" : add ? "bg-test-pass" : ""}`} aria-hidden /><pre className="whitespace-pre pr-4">{toks.length ? toks.map((t, j) => <span key={j} style={{ color: add ? "#4ade80" : t.color }}>{t.content}</span>) : " "}</pre></div>); })}</>;
}
