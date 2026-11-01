import { useCallback, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { FAQ_ITEMS } from "./data";
import { EASE_OUT } from "./motion";
import { Reveal } from "./Reveal";

export function FaqCarousel() {
  const [index, setIndex] = useState(0);
  const [dir, setDir] = useState(1);
  const go = useCallback((next: number, d: number) => {
    setDir(d);
    setIndex(((next % FAQ_ITEMS.length) + FAQ_ITEMS.length) % FAQ_ITEMS.length);
  }, []);
  const item = FAQ_ITEMS[index];
  return (
    <section id="faq" className="scroll-mt-16 border-t border-line bg-panel/40" aria-label="Questions and answers">
      <div className="mx-auto max-w-6xl px-5 py-16">
        <Reveal>
          <h2 className="font-display text-[32px] font-light tracking-[-0.03em]">Questions, answered</h2>
          <p className="mt-2 max-w-xl text-[17px] text-zinc-300">What Forge Guard does, what it never does, and what to expect from the hosted demo.</p>
        </Reveal>
        <div className="mt-8 rounded-md border border-line bg-panel p-5 sm:p-7">
          <div className="flex items-center justify-between gap-3">
            <p className="font-mono text-[11px] text-ember-bright" aria-live="polite">QUESTION {index + 1} / {FAQ_ITEMS.length}</p>
            <div className="flex gap-2">
              <button type="button" onClick={() => go(index - 1, -1)} aria-label="Previous question" className="rounded-sm border border-line px-3 py-2 font-mono text-[13px] text-zinc-200 hover:border-zinc-500 focus-visible:outline-2 focus-visible:outline-ember">←</button>
              <button type="button" onClick={() => go(index + 1, 1)} aria-label="Next question" className="rounded-sm border border-line px-3 py-2 font-mono text-[13px] text-zinc-200 hover:border-zinc-500 focus-visible:outline-2 focus-visible:outline-ember">→</button>
            </div>
          </div>
          <div className="relative mt-4 min-h-44 overflow-hidden sm:min-h-36">
            <AnimatePresence mode="wait" initial={false} custom={dir}>
              <motion.div key={index} initial={{ opacity: 0, x: 32 * dir }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -32 * dir }} transition={{ duration: 0.3, ease: EASE_OUT }}>
                <h3 className="text-[22px] font-bold leading-snug">{item.q}</h3>
                <p className="mt-3 max-w-3xl text-[16px] leading-relaxed text-zinc-300">{item.a}</p>
              </motion.div>
            </AnimatePresence>
          </div>
          <div className="mt-5 flex flex-wrap gap-2" role="tablist" aria-label="Choose a question">
            {FAQ_ITEMS.map((f, i) => (
              <button key={f.q} type="button" role="tab" aria-selected={i === index} onClick={() => go(i, i > index ? 1 : -1)}
                className={`rounded-sm px-2.5 py-1.5 font-mono text-[10px] focus-visible:outline-2 focus-visible:outline-ember ${i === index ? "bg-ember text-white" : "border border-line text-zinc-400 hover:text-zinc-200"}`}>
                Q{i + 1}
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
