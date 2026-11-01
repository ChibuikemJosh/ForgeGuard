import { motion } from "motion/react";
import { ForgeGraph } from "./ForgeGraph";
import { EASE_OUT, lineReveal } from "./motion";

const STATS = [
  { label: "LANGUAGE", value: "Python only" },
  { label: "FINDINGS", value: "Evidence-gated" },
  { label: "AI CHANGES", value: "Approve-first" },
] as const;

export function Hero() {
  return (
    <section className="mx-auto max-w-6xl px-5 pb-16 pt-12 sm:pt-16">
      <div className="grid items-start gap-10 lg:grid-cols-12">
        <div className="lg:col-span-5">
          <motion.p
            className="flex items-center gap-2.5 font-mono text-[11px] font-medium tracking-[0.18em] text-ember-bright"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.55, duration: 0.5 }}
          >
            <motion.span
              className="size-1.5 rounded-full bg-ember"
              animate={{ opacity: [1, 0.25, 1], scale: [1, 0.8, 1] }}
              transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
              aria-hidden
            />
            AI SECURITY INVESTIGATION — NO-AUTH HACKATHON DEMO
          </motion.p>

          <h1 className="mt-5 font-display text-[44px] font-light leading-[1.05] tracking-[-0.035em] text-zinc-50 sm:text-[64px]">
            <span className="block overflow-hidden pb-1">
              <motion.span className="block" variants={lineReveal} custom={1.6} initial="hidden" animate="visible">
                Upload code.
              </motion.span>
            </span>
            <span className="block overflow-hidden pb-1">
              <motion.span className="block text-zinc-400" variants={lineReveal} custom={1.72} initial="hidden" animate="visible">
                Find real auth bugs.
              </motion.span>
            </span>
          </h1>

          <motion.p
            className="mt-6 max-w-md text-[18px] leading-relaxed text-zinc-300"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.9, duration: 0.6, ease: EASE_OUT }}
          >
            Forge Guard turns a Python folder into a SourceGraph, then Meta Muse checks it against rules
            like “customers may only access their own orders”. Findings are potential, evidence-validated,
            and fixes need your approval before anything is written.
          </motion.p>

          <motion.div
            className="mt-8 flex flex-wrap gap-3"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 2.02, duration: 0.6, ease: EASE_OUT }}
          >
            <motion.a
              href="/workspace"
              className="rounded-sm bg-ember px-5 py-3 text-[15px] font-bold text-white hover:bg-ember-soft focus-visible:outline-2 focus-visible:outline-white"
              whileHover={{ y: -2 }}
              whileTap={{ scale: 0.98 }}
            >
              Try the live workspace
            </motion.a>
            <motion.a
              href="#how-it-works"
              className="rounded-sm border border-line bg-panel px-5 py-3 text-[15px] font-bold text-zinc-100 hover:border-zinc-500 focus-visible:outline-2 focus-visible:outline-ember"
              whileHover={{ y: -2 }}
              whileTap={{ scale: 0.98 }}
            >
              See how it works
            </motion.a>
          </motion.div>

          <motion.dl
            className="mt-10 grid grid-cols-3 gap-4 border-t border-line pt-5"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 2.2, duration: 0.7 }}
          >
            {STATS.map((stat) => (
              <div key={stat.label}>
                <dt className="font-mono text-[10px] tracking-[0.14em] text-zinc-500">{stat.label}</dt>
                <dd className="mt-1.5 font-display text-[17px] font-light tracking-tight text-zinc-100">{stat.value}</dd>
              </div>
            ))}
          </motion.dl>
        </div>

        <motion.div
          className="lg:col-span-7"
          initial={{ opacity: 0, clipPath: "inset(0 0 100% 0)" }}
          animate={{ opacity: 1, clipPath: "inset(0 0 0% 0)" }}
          transition={{ delay: 1.7, duration: 0.9, ease: EASE_OUT }}
        >
          <ForgeGraph />
          <p className="mt-3 font-mono text-[11px] leading-relaxed text-zinc-500">
            ↑ A real slice of this repo — health endpoint, schema, service and its test — as Forge nodes. Your project gets the same treatment, at folder / file / function level.
          </p>
        </motion.div>
      </div>
    </section>
  );
}
