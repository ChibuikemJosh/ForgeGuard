import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { EASE_OUT } from "./motion";
import { Reveal } from "./Reveal";

type WorkflowTab = "code" | "graph" | "ai";

const TABS: readonly { id: WorkflowTab; label: string }[] = [
  { id: "code", label: "1 · Edit code" },
  { id: "graph", label: "2 · See the graph" },
  { id: "ai", label: "3 · Approve AI change" },
];

/**
 * Health-endpoint sample with hand-placed syntax colors:
 * ember for keywords, green for strings, sky for the defined function,
 * muted italic for the comment. Plain spans keep it deterministic.
 */
function HealthCodeSample() {
  const kw = "text-ember-bright";
  const str = "text-test-pass";
  const fn = "text-[#7dd3fc]";
  const com = "italic text-zinc-500";
  const punc = "text-zinc-400";
  return (
    <pre className="overflow-x-auto p-4 font-mono text-[11.5px] leading-relaxed sm:p-5 sm:text-[12.5px]" aria-label="Sample Python endpoint">
      <code>
        <span className={com}># app/api/health.py</span>{"\n"}
        <span className={kw}>from</span> <span className="text-zinc-200">fastapi</span> <span className={kw}>import</span> <span className="text-zinc-200">APIRouter</span>{"\n\n"}
        <span className="text-zinc-200">router</span> <span className={punc}>=</span> <span className="text-zinc-200">APIRouter</span><span className={punc}>()</span>{"\n\n"}
        <span className={fn}>@router.get</span><span className={punc}>(</span><span className={str}>&quot;/api/health&quot;</span><span className={punc}>)</span>{"\n"}
        <span className={kw}>def</span> <span className={fn}>health</span><span className={punc}>():</span>{"\n"}
        {"    "}<span className={kw}>return</span> <span className={punc}>{"{"}</span><span className={str}>&quot;status&quot;</span><span className={punc}>:</span> <span className={str}>&quot;ok&quot;</span><span className={punc}>,</span> <span className={str}>&quot;service&quot;</span><span className={punc}>:</span> <span className={str}>&quot;forge-api&quot;</span><span className={punc}>{"}"}</span>
      </code>
    </pre>
  );
}

export function WorkflowTabs() {
  const [tab, setTab] = useState<WorkflowTab>("code");

  return (
    <div className="min-w-0">
      <div className="flex flex-col gap-2 min-[560px]:flex-row min-[560px]:flex-wrap" role="tablist" aria-label="Forge workflow">
        {TABS.map((item) => {
          const isActive = tab === item.id;
          return (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => setTab(item.id)}
              className={`relative w-full rounded-sm border px-4 py-2.5 text-[14px] font-bold focus-visible:outline-2 focus-visible:outline-ember min-[560px]:w-auto sm:text-[15px] ${
                isActive ? "border-ember text-white" : "border-line bg-panel text-zinc-300 hover:border-zinc-600 hover:text-white"
              }`}
            >
              {isActive && (
                <motion.span
                  layoutId="workflow-tab-pill"
                  className="absolute inset-0 bg-ember"
                  transition={{ type: "spring", stiffness: 480, damping: 38 }}
                />
              )}
              <span className="relative z-10">{item.label}</span>
            </button>
          );
        })}
      </div>

      <div className="relative mt-4 overflow-hidden rounded-md border border-line bg-panel" role="tabpanel">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={tab}
            initial={{ opacity: 0, x: 22 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -22 }}
            transition={{ duration: 0.32, ease: EASE_OUT }}
          >
        {tab === "code" && <HealthCodeSample />}

        {tab === "graph" && (
          <div className="p-4 sm:p-6">
            <p className="text-[16px] leading-relaxed text-zinc-200 sm:text-[17px]">
              The same endpoint, as a node. Its <span className="font-mono text-[13px] text-ember-bright sm:text-[14px]">data</span> edge
              feeds the frontend client, its <span className="font-mono text-[13px] text-ember-bright sm:text-[14px]">dependency</span>{" "}
              edge is covered by <span className="font-mono text-[13px] sm:text-[14px]">test_health</span>.
            </p>
            <p className="mt-4 overflow-x-auto whitespace-nowrap pb-1 font-mono text-[11px] leading-loose text-zinc-400 sm:text-[12px]">
              GET /api/health ──data──▶ fetchBackendHealth()
              <br />
              GET /api/health ──dependency──▶ test_health ✓ passing
            </p>
          </div>
        )}

        {tab === "ai" && (
          <div className="p-4 sm:p-6">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-sm bg-ember px-2 py-0.5 font-mono text-[10px] font-semibold text-white">PROPOSAL</span>
              <span className="break-all font-mono text-[12px] text-zinc-300">Add GET /api/projects</span>
            </div>
            <ul className="mt-4 space-y-2 text-[15px] leading-relaxed text-zinc-300 sm:text-[16px]">
              <li>
                + New node <span className="font-mono text-[13px]">Projects API</span> — touches{" "}
                <span className="break-all font-mono text-[13px]">app/api/projects.py</span>
              </li>
              <li>
                + Data edge → <span className="font-mono text-[13px]">ForgeProject</span> schema · no existing edges removed
              </li>
            </ul>
            <div className="mt-5 flex flex-col gap-2 min-[420px]:flex-row min-[420px]:flex-wrap">
              <button type="button" className="w-full rounded-sm bg-ember px-4 py-2.5 text-[14px] font-bold text-white hover:bg-ember-soft focus-visible:outline-2 focus-visible:outline-white min-[420px]:w-auto">
                Approve proposal
              </button>
              <button type="button" className="w-full rounded-sm border border-line px-4 py-2.5 text-[14px] font-bold text-zinc-200 hover:border-zinc-500 focus-visible:outline-2 focus-visible:outline-ember min-[420px]:w-auto">
                Request changes
              </button>
            </div>
          </div>
        )}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

export function WorkflowSection() {
  return (
    <section id="workflow" className="scroll-mt-16 border-t border-line bg-panel/40">
      <div className="mx-auto w-full max-w-6xl px-4 py-14 sm:px-5 sm:py-16">
        <div className="grid gap-8 lg:grid-cols-12">
          <Reveal className="lg:col-span-4">
            <h2 className="font-display text-[28px] font-light leading-[1.1] tracking-[-0.03em] sm:text-[32px]">
              One project,
              <span className="block font-light text-zinc-400">two views.</span>
            </h2>
            <p className="mt-4 text-[16px] leading-relaxed text-zinc-300 sm:text-[17px]">
              Write Python as usual. Forge keeps the graph honest — and puts a human approval gate between an AI
              suggestion and your source files.
            </p>
            <p className="mt-5 font-mono text-[12px] text-zinc-500">Try the three tabs →</p>
          </Reveal>
          <Reveal className="lg:col-span-8" delay={0.1}>
            <WorkflowTabs />
          </Reveal>
        </div>
      </div>
    </section>
  );
}
