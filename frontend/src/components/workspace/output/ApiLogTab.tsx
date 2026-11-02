import type { ApiLogEntry } from "../../../features/project/types";

export function ApiLogTab({ logs }: { logs: ApiLogEntry[] }) {
  return (
    <div className="p-2 font-mono text-[10px] text-zinc-400">
      {logs.length === 0 ? <p>No API calls yet.</p> : logs.map((l) => (
        <div key={l.id}>{l.at} · {l.method} {l.path} · {l.status} · {l.durationMs}ms</div>
      ))}
    </div>
  );
}
