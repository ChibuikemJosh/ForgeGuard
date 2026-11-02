import { motion } from "motion/react";
import { Link } from "react-router-dom";
import { Reveal } from "./Reveal";

export function ClosingSection() {
  return (
    <section className="border-t border-line">
      <div className="mx-auto flex max-w-6xl flex-wrap items-end justify-between gap-6 px-5 py-16">
        <Reveal>
          <h2 className="max-w-lg font-display text-[36px] font-light leading-[1.1] tracking-[-0.03em]">
            Bring a folder. Leave with evidence.
          </h2>
          <p className="mt-3 text-[17px] text-zinc-300">Try the sample, or upload your own Python project — no account, nothing executed, nothing written without your approval.</p>
        </Reveal>
        <motion.div
          className="rounded-sm bg-ember px-6 py-3.5 text-[15px] font-bold text-white hover:bg-ember-soft focus-visible:outline-2 focus-visible:outline-white"
          whileHover={{ y: -2 }}
          whileTap={{ scale: 0.98 }}
        >
          <Link to="/workspace" className="rounded-sm bg-ember px-6 py-3.5 text-[15px] font-bold text-white hover:bg-ember-soft focus-visible:outline-2 focus-visible:outline-white">
          Open the workspace ↑
          </Link>
        </motion.div>
      </div>
    </section>
  );
}

export function SiteFooter() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-2 px-5 py-6 font-mono text-[11px] text-zinc-500">
        <span className="font-sans text-[15px] font-black text-zinc-100">ForgeGuard</span>
        <span>React + FastAPI · Hackathon build</span>
        <span className="sm:ml-auto">SourceGraph · Muse investigation · Evidence-gated fixes</span>
      </div>
    </footer>
  );
}
