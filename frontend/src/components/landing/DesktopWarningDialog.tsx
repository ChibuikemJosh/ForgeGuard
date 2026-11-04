/** Centered warning that the workspace is a desktop-first experience. */
export function DesktopWarningDialog({ open, remember, onRememberChange, onContinue, onClose }: {
  open: boolean; remember: boolean; onRememberChange: (v: boolean) => void; onContinue: () => void; onClose: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 grid place-items-center p-4" role="alertdialog" aria-modal="true" aria-labelledby="desktop-notice-title">
      <button type="button" aria-label="Close dialog" onClick={onClose} className="absolute inset-0 cursor-default bg-black/70" />
      <div className="relative w-full max-w-md rounded-lg border border-line bg-panel p-5 shadow-2xl">
        <p className="font-mono text-[10px] tracking-[0.14em] text-ember-bright">DESKTOP-FIRST WORKSPACE</p>
        <h2 id="desktop-notice-title" className="mt-2 text-[20px] font-bold tracking-tight text-zinc-50">Best experienced on a desktop</h2>
        <p className="mt-2 text-[15px] leading-relaxed text-zinc-300">
          The Forge workspace lays graph, code and findings side by side and isn&apos;t mobile-friendly —
          on a small screen the panels stack and the graph is hard to read.
        </p>
        <p className="mt-2 text-[14px] leading-relaxed text-zinc-400">
          This landing page works fine on mobile. Continue anyway, or come back on a wider screen.
        </p>
        <label className="mt-4 flex cursor-pointer items-center gap-2 text-[13px] text-zinc-400">
          <input type="checkbox" checked={remember} onChange={(e) => onRememberChange(e.target.checked)} className="size-4 accent-[#c2410c]" />
          Don&apos;t show this again
        </label>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row">
          <button type="button" onClick={onContinue} autoFocus className="flex-1 rounded-sm bg-ember px-4 py-2.5 text-[14px] font-bold text-white hover:bg-ember-soft focus-visible:outline-2 focus-visible:outline-white">
            Continue to workspace
          </button>
          <button type="button" onClick={onClose} className="flex-1 rounded-sm border border-line px-4 py-2.5 text-[14px] font-bold text-zinc-200 hover:border-zinc-500 focus-visible:outline-2 focus-visible:outline-ember">
            Stay on landing
          </button>
        </div>
      </div>
    </div>
  );
}
