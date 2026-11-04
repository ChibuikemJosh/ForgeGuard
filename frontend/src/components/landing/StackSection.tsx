import { BackendPill } from "./BackendPill";
import { STACK } from "./data";
import { Reveal } from "./Reveal";

export function StackSection() {
  return (
    <section id="stack" className="scroll-mt-16 border-t border-line bg-panel/40">
      <div className="mx-auto w-full max-w-6xl px-4 py-14 sm:px-5 sm:py-16">
        <div className="grid gap-8 lg:grid-cols-12 lg:gap-10">
          <Reveal className="lg:col-span-7">
            <h2 className="font-display text-[24px] font-light tracking-[-0.03em] sm:text-[26px]">Stack</h2>
            <dl className="mt-5 divide-y divide-line border-y border-line">
              {STACK.map((row) => (
                <div key={row.layer} className="grid gap-1 py-4 sm:grid-cols-4">
                  <dt className="pt-0.5 font-mono text-[12px] font-medium text-ember-bright">{row.layer}</dt>
                  <dd className="text-[15px] leading-relaxed text-zinc-200 sm:col-span-3 sm:text-[16px]">{row.items}</dd>
                </div>
              ))}
            </dl>
          </Reveal>

          <Reveal className="lg:col-span-5" delay={0.1}>
            <h2 className="font-display text-[24px] font-light tracking-[-0.03em] sm:text-[26px]">Live right now</h2>
            <div className="mt-5 rounded-md border border-line bg-panel p-4 sm:p-5">
              <BackendPill />
              <p className="mt-3 text-[15px] leading-relaxed text-zinc-300 sm:text-[16px]">
                This status is the real result of <span className="break-all font-mono text-[13px]">GET /api/health</span> from
                this page — no hardcoded success. Start the backend and watch it flip.
              </p>
              <pre className="mt-4 max-w-full overflow-x-auto rounded-sm bg-coal p-3 font-mono text-[11px] text-zinc-300 sm:text-[11.5px]">
                <code>cd backend &amp;&amp; uvicorn app.main:app --reload --reload-dir app --port 8000</code>
              </pre>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
