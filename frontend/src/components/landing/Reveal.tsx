import type { ReactNode } from "react";
import { motion } from "motion/react";
import { riseIn, VIEWPORT_ONCE } from "./motion";

interface RevealProps {
  children: ReactNode;
  delay?: number;
  className?: string;
}

/** One-shot section entrance on scroll into view. Wrap a block once —
 *  do not nest Reveals or put one on every card. */
export function Reveal({ children, delay = 0, className }: RevealProps) {
  return (
    <motion.div
      className={`min-w-0 ${className ?? ""}`}
      variants={riseIn}
      custom={delay}
      initial="hidden"
      whileInView="visible"
      viewport={VIEWPORT_ONCE}
    >
      {children}
    </motion.div>
  );
}
