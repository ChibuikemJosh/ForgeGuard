import { motion } from "motion/react";
import { CONNECTIONS } from "./data";
import { staggerChild, staggerParent, VIEWPORT_ONCE } from "./motion";
import { Reveal } from "./Reveal";

const PRINCIPLES = [
  { title: "Real, not decorative.", body: "The model maps to actual source — never a diagram that drifts." },
  { title: "Grown, not speculated.", body: "Schema is added only when a feature consumes it." },
  { title: "One source of truth.", body: "Frontend and backend stay aligned on the same model." },
] as const;

export function ModelSection() {
  return (
    <section id="model" className="scroll-mt-16 border-t border-line">
      <div className="mx-auto w-full max-w-6xl px-4 py-14 sm:px-5 sm:py-16">
        <Reveal>
          <h2 className="font-display text-[28px] font-light leading-tight tracking-[-0.03em] sm:text-[32px]">Three edges. Three meanings.</h2>
          <p className="mt-2 max-w-xl text-[16px] leading-relaxed text-zinc-300 sm:text-[17px]">
            Connection kinds are never interchangeable — each is validated on its own rules.
          </p>
        </Reveal>

        <Reveal className="mt-8">
          <div className="divide-y divide-line rounded-md border border-line sm:hidden">
            {CONNECTIONS.map((row) => (
              <div key={row.kind} className="p-4">
                <p className="font-mono text-[13px] font-semibold text-ember-bright">{row.kind}</p>
                <p className="mt-1.5 text-[15px] leading-relaxed text-zinc-200">{row.meaning}</p>
                <p className="mt-1.5 break-all font-mono text-[11px] leading-relaxed text-zinc-400">{row.example}</p>
              </div>
            ))}
          </div>
          <div className="hidden overflow-x-auto rounded-md border border-line sm:block">
          <table className="w-full min-w-140 text-left text-[15px]">
            <thead>
              <tr className="border-b border-line bg-panel font-mono text-[11px] tracking-[0.12em] text-zinc-400">
                <th scope="col" className="px-4 py-3 font-medium">KIND</th>
                <th scope="col" className="px-4 py-3 font-medium">MEANING</th>
                <th scope="col" className="px-4 py-3 font-medium">IN THIS REPO</th>
              </tr>
            </thead>
            <motion.tbody
              className="divide-y divide-line"
              variants={staggerParent}
              initial="hidden"
              whileInView="visible"
              viewport={VIEWPORT_ONCE}
            >
              {CONNECTIONS.map((row) => (
                <motion.tr key={row.kind} variants={staggerChild} className="transition-colors hover:bg-panel/70">
                  <td className="px-4 py-4 font-mono text-[13px] font-semibold text-ember-bright">{row.kind}</td>
                  <td className="px-4 py-4 text-zinc-200">{row.meaning}</td>
                  <td className="px-4 py-4 font-mono text-[12px] text-zinc-400">{row.example}</td>
                </motion.tr>
              ))}
            </motion.tbody>
          </table>
          </div>
        </Reveal>

        <motion.div
          className="mt-8 grid gap-6 sm:grid-cols-3"
          variants={staggerParent}
          initial="hidden"
          whileInView="visible"
          viewport={VIEWPORT_ONCE}
        >
          {PRINCIPLES.map((principle) => (
            <motion.p key={principle.title} variants={staggerChild} className="text-[15px] leading-relaxed text-zinc-300 sm:text-[16px]">
              <strong className="block text-[16px] text-white sm:text-[17px]">{principle.title}</strong>
              {principle.body}
            </motion.p>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
