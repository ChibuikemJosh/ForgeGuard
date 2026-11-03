import { useEffect, useState } from "react";
import { AnimatePresence, MotionConfig, motion, useReducedMotion, useScroll, useSpring } from "motion/react";
import { BootScreen } from "../components/landing/BootScreen";
import { Capabilities } from "../components/landing/Capabilities";
import { Hero } from "../components/landing/Hero";
import { LandingNav } from "../components/landing/LandingNav";
import { ModelSection } from "../components/landing/ModelSection";
import { ClosingSection, SiteFooter } from "../components/landing/SiteFooter";
import { StackSection } from "../components/landing/StackSection";
import { Ticker } from "../components/landing/Ticker";
import { WorkflowSection } from "../components/landing/WorkflowTabs";
import { ScrollStory } from "../components/landing/ScrollStory";
import { FaqCarousel } from "../components/landing/FaqCarousel";

const BOOT_MS = 1500;

export default function Home() {
  const reduceMotion = useReducedMotion();
  const [booting, setBooting] = useState(!reduceMotion);
  const { scrollYProgress } = useScroll();
  const progress = useSpring(scrollYProgress, { stiffness: 120, damping: 28, mass: 0.4 });

  useEffect(() => {
    if (!booting) return;
    const timer = window.setTimeout(() => setBooting(false), BOOT_MS);
    return () => window.clearTimeout(timer);
  }, [booting]);

  return (
    <MotionConfig reducedMotion="user">
      <div className="min-h-screen overflow-x-clip bg-coal font-sans text-zinc-100">
        <AnimatePresence>{booting ? <BootScreen key="boot" /> : null}</AnimatePresence>

        <a
          href="#capabilities"
          className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-ember focus:px-3 focus:py-2 focus:text-white"
        >
          Skip to content
        </a>

        <LandingNav />
        <motion.div
          className="sticky top-14 z-40 h-0.5 origin-left bg-ember"
          style={{ scaleX: progress }}
          aria-hidden
        />

        <main>
          <Hero />
          <Ticker />
          <Capabilities />
          <ScrollStory />
          <WorkflowSection />
          <ModelSection />
          <StackSection />
          <FaqCarousel />
          <ClosingSection />
        </main>
        <SiteFooter />
      </div>
    </MotionConfig>
  );
}
