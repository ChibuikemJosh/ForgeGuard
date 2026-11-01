import { BackendPill } from "./BackendPill";
import { STACK } from "./data";
import { Reveal } from "./Reveal";

export function StackSection() {
  return (
    <section id="stack" className="scroll-mt-16 border-t border-line bg-panel/40">
      <div className="mx-auto max-w-6xl px-5 py-16">
        <div className="grid gap-10 lg:grid-cols-12">
          <Reveal className="lg:col-span-7">
            <h2 className="font-display text-[26px] font-light tracking-[-0.03em]">Stack</h2>
            <dl className="mt-5 divide-y divide-line border-y border-line">
              {STACK.map((row) => (
                <div key={row.layer} className="grid gap-1 py-4 sm:grid-cols-4">
                  <dt className="pt-0.5 font-mono text-[12px] font-medium text-ember-bright">{row.layer}</dt>
                  <dd className="text-[16px] text-zinc-200 sm:col-span-3">{row.items}</dd>
                </div>
              ))}
            </dl>
          </Reveal>

          <Reveal className="lg:col-span-5" delay={0.1}>
            <h2 className="font-display text-[26px] font-light tracking-[-0.03em]">Live right now</h2>
            <div className="mt-5 rounded-md border border-line bg-panel p-5">
              <BackendPill />
              <p className="mt-3 text-[16px] leading-relaxed text-zinc-300">
                This status is the real result of <span className="font-mono text-[13px]">GET /api/health</span> from
                this page — no hardcoded success. Start the backend and watch it flip.
              </p>
              <pre className="mt-4 overflow-x-auto rounded-sm bg-coal p-3 font-mono text-[11.5px] text-zinc-300">
                <code>cd backend &amp;&amp; uvicorn app.main:app --reload --reload-dir app --port 8000</code>
              </pre>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
