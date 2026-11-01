import { motion, useReducedMotion } from "motion/react";

/** Smooth AI/parsing indicator: scanning beam over skeleton cards + orbiting nodes. */
export function AiLoading({ label, detail }: { label: string; detail?: string }) {
  const reduce = useReducedMotion();
  return (
    <div className="relative grid h-full place-items-center overflow-hidden rounded-lg border border-line bg-panel p-6" role="status" aria-live="polite" aria-label={label}>
      <div aria-hidden className="pointer-events-none absolute inset-0 opacity-60" style={{ backgroundImage: "radial-gradient(circle, #2a2a2e 1px, transparent 1px)", backgroundSize: "22px 22px" }} />
      {!reduce ? <motion.div aria-hidden className="pointer-events-none absolute inset-x-0 h-24 bg-gradient-to-b from-transparent via-ember/10 to-transparent" animate={{ top: ["-10%", "110%"] }} transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }} /> : null}
      <div className="relative flex w-full max-w-sm flex-col items-center">
        <div className="relative flex h-20 items-center justify-center gap-3" aria-hidden>
          {[0, 1, 2].map((i) => (
            <motion.span key={i} className="block rounded-md border border-line bg-panel-2" style={{ width: 52 - i * 6, height: 36 }}
              animate={reduce ? undefined : { y: [0, -8, 0], borderColor: ["#262629", "#c2410c", "#262629"] }}
              transition={{ duration: 1.6, repeat: Infinity, delay: i * 0.22, ease: "easeInOut" }} />
          ))}
          {!reduce ? <motion.span className="absolute h-px w-44 bg-ember/60" animate={{ scaleX: [0.3, 1, 0.3], opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }} /> : null}
        </div>
        <p className="mt-2 text-center text-[13px] font-medium text-zinc-100">{label}</p>
        {detail ? <p className="mt-1 text-center font-mono text-[10px] leading-relaxed text-zinc-500">{detail}</p> : null}
        <div className="mt-4 flex w-full flex-col gap-2" aria-hidden>
          {[82, 64, 72].map((w, i) => (
            <motion.div key={i} className="h-2 overflow-hidden rounded-full bg-ide-hover" animate={reduce ? undefined : { opacity: [0.5, 1, 0.5] }} transition={{ duration: 1.4, repeat: Infinity, delay: i * 0.18 }}>
              <motion.div className="h-full rounded-full bg-ember/70" animate={reduce ? undefined : { x: ["-100%", "220%"] }} transition={{ duration: 1.6, repeat: Infinity, delay: i * 0.2, ease: "easeInOut" }} style={{ width: `${w / 2.2}%` }} />
            </motion.div>
          ))}
        </div>
        <span className="mt-3 flex gap-1.5" aria-hidden>
          {[0, 1, 2].map((i) => <motion.span key={i} className="size-1.5 rounded-full bg-ember-bright" animate={reduce ? undefined : { scale: [1, 1.7, 1], opacity: [0.4, 1, 0.4] }} transition={{ duration: 1.1, repeat: Infinity, delay: i * 0.16 }} />)}
        </span>
      </div>
    </div>
  );
}

export function AiInlinePulse({ label }: { label: string }) {
  const reduce = useReducedMotion();
  return (
    <span className="inline-flex items-center gap-2" role="status" aria-live="polite">
      <span className="flex gap-1" aria-hidden>{[0, 1, 2].map((i) => <motion.span key={i} className="size-1.5 rounded-full bg-ember-bright" animate={reduce ? undefined : { scale: [1, 1.6, 1], opacity: [0.4, 1, 0.4] }} transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }} />)}</span>
      <span>{label}</span>
    </span>
  );
}
