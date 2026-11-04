import { useRef, useState, useEffect } from "react";
import { motion, useReducedMotion, useScroll, useTransform } from "motion/react";
import type { MotionValue } from "motion/react";
import { HOW_STEPS } from "./data";
import { Reveal } from "./Reveal";

function StepPanel({ index, progress }: { index: number; progress: MotionValue<number> }) {
  const n = HOW_STEPS.length;
  const start = index / n;
  const end = (index + 1) / n;
  const opacity = useTransform(progress, [start, start + 0.04, end - 0.04, end], [0, 1, 1, index === n - 1 ? 1 : 0]);
  const y = useTransform(progress, [start, end], [28, index === n - 1 ? 0 : -28]);
  const step = HOW_STEPS[index];
  return (
    <motion.article style={{ opacity, y }} className="absolute inset-0 flex flex-col justify-center overflow-y-auto" aria-hidden={false}>
      <p className="font-mono text-[12px] text-ember-bright sm:text-[13px]">{step.n} / 0{n}</p>
      <h3 className="mt-2 font-display text-[28px] font-light leading-[1.12] tracking-[-0.02em] min-[420px]:text-[32px] sm:mt-3 sm:text-[44px]">{step.title}</h3>
      <p className="mt-3 max-w-xl text-[15px] leading-relaxed text-zinc-300 sm:mt-4 sm:text-[17px]">{step.body}</p>
      <p className="mt-4 break-all rounded-sm border border-line bg-coal px-3 py-2 font-mono text-[10px] leading-relaxed text-zinc-400 sm:mt-5 sm:text-[11px]">{step.mono}</p>
    </motion.article>
  );
}

/** Pinned scroll story: the section is tall and the panel stays fixed while
 *  scroll progress advances the steps — you scroll through the story before
 *  the page continues. Reduced-motion users get the plain list instead. */
export function ScrollStory() {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  const barScale = useTransform(scrollYProgress, [0, 1], [0, 1]);
  const [active, setActive] = useState(0);
  useEffect(() => scrollYProgress.on("change", (v) => setActive(Math.min(HOW_STEPS.length - 1, Math.floor(v * HOW_STEPS.length)))), [scrollYProgress]);

  if (reduce) {
    return (
      <section id="how-it-works" className="scroll-mt-16 border-t border-line">
        <div className="mx-auto w-full max-w-6xl px-4 py-14 sm:px-5 sm:py-16">
          <Reveal><h2 className="font-display text-[28px] font-light tracking-[-0.03em] sm:text-[32px]">How it works</h2></Reveal>
          <div className="mt-8 divide-y divide-line border-y border-line">
            {HOW_STEPS.map((s) => (
              <article key={s.n} className="grid gap-2 py-5 sm:grid-cols-12">
                <span className="font-mono text-[13px] text-ember-bright sm:col-span-1">{s.n}</span>
                <h3 className="text-[18px] font-bold sm:col-span-4">{s.title}</h3>
                <div className="sm:col-span-7">
                  <p className="text-[15px] leading-relaxed text-zinc-300 sm:text-[16px]">{s.body}</p>
                  <p className="mt-3 break-all rounded-sm border border-line bg-coal px-3 py-2 font-mono text-[10px] leading-relaxed text-zinc-400 sm:text-[11px]">{s.mono}</p>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>
    );
  }

  return (
    <section id="how-it-works" className="scroll-mt-16 border-t border-line" aria-label="How Forge Guard works">
      <div ref={ref} className="relative" style={{ height: `${HOW_STEPS.length * 90}svh` }}>
        <div className="sticky top-0 flex h-dvh flex-col overflow-hidden">
          <div className="mx-auto w-full min-w-0 max-w-6xl px-4 pt-16 sm:px-5 sm:pt-20">
            <p className="font-mono text-[10px] tracking-[0.14em] text-ember-bright sm:text-[11px] sm:tracking-[0.18em]">HOW IT WORKS — KEEP SCROLLING</p>
            <h2 className="mt-2 font-display text-[24px] font-light leading-tight tracking-[-0.03em] sm:text-[28px]">From folder to fix, in five steps</h2>
            <div className="mt-5 h-1 w-full bg-line" role="progressbar" aria-valuemin={1} aria-valuemax={HOW_STEPS.length} aria-valuenow={active + 1} aria-label="How it works progress">
              <motion.div className="h-full origin-left bg-ember" style={{ scaleX: barScale }} />
            </div>
            <div className="mt-3 flex gap-2" aria-hidden>
              {HOW_STEPS.map((s, i) => (
                <span key={s.n} className={`rounded-sm px-2 py-1 font-mono text-[10px] ${i === active ? "bg-ember text-white" : "border border-line text-zinc-500"}`}>{s.n}</span>
              ))}
            </div>
          </div>
          <div className="relative mx-auto w-full min-w-0 max-w-6xl flex-1 px-4 pb-10 sm:px-5 sm:pb-16">
            {HOW_STEPS.map((s, i) => <StepPanel key={s.n} index={i} progress={scrollYProgress} />)}
          </div>
        </div>
      </div>
    </section>
  );
}
