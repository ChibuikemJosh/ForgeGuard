import { motion } from "motion/react";
import { DesktopWarningDialog } from "./DesktopWarningDialog";
import { useDesktopWarning } from "./useDesktopWarning";
import { Reveal } from "./Reveal";

export function ClosingSection() {
  const desktop = useDesktopWarning();
  return (
    <section className="border-t border-line">
      <div className="mx-auto flex w-full max-w-6xl flex-col items-start gap-6 px-4 py-14 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between sm:px-5 sm:py-16">
        <Reveal className="min-w-0">
          <h2 className="max-w-lg font-display text-[30px] font-light leading-[1.1] tracking-[-0.03em] sm:text-[36px]">
            Bring a folder. Leave with evidence.
          </h2>
          <p className="mt-3 text-[16px] leading-relaxed text-zinc-300 sm:text-[17px]">Try the sample, or upload your own Python project — no account, nothing executed, nothing written without your approval.</p>
        </Reveal>
        <motion.button
          type="button"
          onClick={() => desktop.requestWorkspace()}
          className="w-full rounded-sm bg-ember px-6 py-3.5 text-center text-[15px] font-bold text-white hover:bg-ember-soft focus-visible:outline-2 focus-visible:outline-white sm:w-auto"
          whileHover={{ y: -2 }}
          whileTap={{ scale: 0.98 }}
        >
          Open the workspace ↑
        </motion.button>
        <DesktopWarningDialog open={desktop.noticeOpen} remember={desktop.remember} onRememberChange={desktop.setRemember} onContinue={desktop.continueToWorkspace} onClose={desktop.closeNotice} />
      </div>
    </section>
  );
}

export function SiteFooter() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-6 font-mono text-[10px] text-zinc-500 sm:px-5 sm:text-[11px]">
        <span className="font-sans text-[15px] font-black text-zinc-100">ForgeGuard</span>
        <span>React + FastAPI · Hackathon build</span>
        <span className="w-full sm:w-auto sm:ml-auto">SourceGraph · Muse investigation · Evidence-gated fixes</span>
      </div>
    </footer>
  );
}
