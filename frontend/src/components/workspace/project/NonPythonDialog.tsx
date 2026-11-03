interface Props {
  open: boolean;
  message: string;
  sampleLabel: string | null;
  onUseSample: (() => void) | null;
  onChooseAnother: () => void;
  onClose: () => void;
}

/** Centered warning shown when an uploaded folder has no Python to analyse. */
export function NonPythonDialog({ open, message, sampleLabel, onUseSample, onChooseAnother, onClose }: Props) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 grid place-items-center p-4" role="alertdialog" aria-modal="true" aria-labelledby="non-python-title">
      <button type="button" aria-label="Close dialog" onClick={onClose} className="absolute inset-0 cursor-default bg-black/70" />
      <div className="relative w-full max-w-md rounded-lg border border-line bg-panel p-5 shadow-2xl">
        <p className="font-mono text-[10px] tracking-[0.14em] text-sev-warning">PYTHON PROJECTS ONLY — FOR NOW</p>
        <h2 id="non-python-title" className="mt-2 text-[17px] font-semibold text-zinc-50">No Python files found in that folder</h2>
        <p className="mt-2 text-[13px] leading-relaxed text-zinc-300">{message}</p>
        <p className="mt-2 text-[12px] leading-relaxed text-zinc-500">
          Forge Guard builds its SourceGraph from Python source code, so JavaScript, Java, Go and other projects can&apos;t be analysed yet.
        </p>
        <div className="mt-4 flex flex-col gap-2">
          {sampleLabel && onUseSample ? (
            <button type="button" onClick={onUseSample} className="w-full rounded bg-ember px-3 py-2 text-[13px] font-semibold text-white hover:bg-ember-soft focus-visible:outline-2 focus-visible:outline-ide-blue">
              Try the sample instead: {sampleLabel}
            </button>
          ) : null}
          <button type="button" onClick={onChooseAnother} className="w-full rounded border border-line px-3 py-2 text-[13px] font-semibold text-zinc-100 hover:bg-ide-hover focus-visible:outline-2 focus-visible:outline-ide-blue">
            Choose another folder
          </button>
          <button type="button" onClick={onClose} className="w-full rounded px-3 py-1.5 font-mono text-[11px] text-zinc-500 hover:text-zinc-300 focus-visible:outline-2 focus-visible:outline-ide-blue">
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}
