interface Props {
  backendOk: boolean | null; projectName: string | null; fileName: string | null;
  investigationStatus: string | null; phase: string; reviewStatus: string | null; applicationStatus: string | null;
}
export function StatusBar({ backendOk, projectName, fileName, investigationStatus, phase, reviewStatus, applicationStatus }: Props) {
  return (
    <footer className="flex h-7 shrink-0 items-center gap-3 overflow-x-auto rounded-lg border border-line bg-ember-deep px-3 font-ui text-[11px] text-orange-100" aria-label="Status bar">
      <span aria-live="polite">{backendOk === null ? "backend: checking…" : backendOk ? "backend: connected" : "backend: unreachable"}</span>
      <span className="truncate">{projectName ?? "no project"}</span>
      {fileName ? <span className="hidden truncate sm:inline">{fileName}</span> : null}
      <span className="hidden md:inline">investigation: {investigationStatus ?? "—"}</span>
      <span className="ml-auto hidden shrink-0 lg:inline">phase: {phase} · review: {reviewStatus ?? "—"} · apply: {applicationStatus ?? "—"}</span>
    </footer>
  );
}
