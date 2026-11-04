import { motion } from "motion/react";
import { CAPABILITIES } from "./data";
import { staggerChild, staggerParent, VIEWPORT_ONCE } from "./motion";
import { Reveal } from "./Reveal";

export function Capabilities() {
  return (
    <section id="capabilities" className="scroll-mt-16 border-t border-line">
      <div className="mx-auto w-full max-w-6xl px-4 py-14 sm:px-5 sm:py-16">
        <Reveal>
          <h2 className="font-display text-[28px] font-light leading-tight tracking-[-0.03em] sm:text-[32px]">What Forge brings</h2>
          <p className="mt-2 max-w-xl text-[16px] leading-relaxed text-zinc-300 sm:text-[17px]">
            Built for hackathon speed, designed for codebases that outlive the weekend.
          </p>
        </Reveal>

        <motion.div
          className="mt-9 divide-y divide-line border-y border-line"
          variants={staggerParent}
          initial="hidden"
          whileInView="visible"
          viewport={VIEWPORT_ONCE}
        >
          {CAPABILITIES.map((capability) => (
            <motion.article
              key={capability.n}
              variants={staggerChild}
              className="group grid min-w-0 gap-2 py-5 transition-colors hover:bg-panel/70 sm:grid-cols-12 sm:gap-4 sm:px-3 sm:py-6"
            >
              <span className="font-mono text-[13px] text-ember-bright transition-transform duration-300 group-hover:translate-x-1 sm:col-span-1">
                {capability.n}
              </span>
              <h3 className="text-[18px] font-bold leading-snug sm:col-span-4 sm:text-[19px]">{capability.title}</h3>
              <p className="text-[15px] leading-relaxed text-zinc-300 sm:col-span-5 sm:text-[16px]">{capability.body}</p>
              <span className="font-mono text-[11px] text-zinc-500 sm:col-span-2 sm:pt-1 sm:text-right">
                {capability.tag} <span className="inline-block text-ember-bright transition-transform duration-300 group-hover:translate-x-1">→</span>
              </span>
            </motion.article>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
