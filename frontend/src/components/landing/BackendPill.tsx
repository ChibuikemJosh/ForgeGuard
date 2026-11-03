import { useEffect, useState } from "react";
import { apiUrl } from "../../services/api/client";

type BackendState = "checking" | "connected" | "offline";

/** Live backend status — pings GET /api/health and shows the real result. */
export function BackendPill() {
  const [state, setState] = useState<BackendState>("checking");

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), 4000);
    fetch(apiUrl("/api/health"), { signal: controller.signal })
      .then((res) => setState(res.ok ? "connected" : "offline"))
      .catch(() => setState("offline"));
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, []);

  const dot =
    state === "connected"
      ? "bg-test-pass shadow-[0_0_8px_rgba(74,222,128,0.9)]"
      : state === "offline"
        ? "bg-sev-critical shadow-[0_0_8px_rgba(248,113,113,0.7)]"
        : "animate-pulse bg-zinc-500";
  const label = state === "connected" ? "Connected" : state === "offline" ? "Offline" : "Checking…";

  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-line bg-panel px-3 py-1.5 font-mono text-[11px] text-zinc-300" role="status" aria-live="polite" title={state === "connected" ? "Backend is reachable" : state === "offline" ? "Backend is unreachable" : "Checking backend status"}>
      <span className={`size-1.5 rounded-full ${dot}`} aria-hidden />
      {label}
    </span>
  );
}
