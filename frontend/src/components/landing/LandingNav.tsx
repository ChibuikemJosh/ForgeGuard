import { Link } from "react-router-dom";
import { NAV_LINKS } from "./data";
import { DesktopWarningDialog } from "./DesktopWarningDialog";
import { useDesktopWarning } from "./useDesktopWarning";

export function LandingNav() {
  const desktop = useDesktopWarning();
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-coal/95">
      <div className="mx-auto flex h-14 w-full max-w-6xl items-center gap-3 px-4 sm:gap-6 sm:px-5">
        <Link to="/" className="flex min-w-0 items-center gap-2 sm:gap-2.5" aria-label="ForgeGuard home">
          <img src="/favicon.svg" alt="" className="size-7 shrink-0 self-center rounded-sm" />
          <span className="truncate text-[17px] font-normal tracking-tight sm:text-[19px]">ForgeGuard</span>
        </Link>
        <nav className="ml-auto hidden items-center gap-4 text-[15px] font-medium text-zinc-300 md:gap-6 lg:flex" aria-label="Primary">
          {NAV_LINKS.map((item) => (
            <a key={item.href} href={item.href} className="hover:text-white focus-visible:outline-2 focus-visible:outline-ember">
              {item.label}
            </a>
          ))}
        </nav>
        <button type="button" onClick={() => desktop.requestWorkspace()} className="ml-auto shrink-0 whitespace-nowrap rounded-sm bg-zinc-100 px-3 py-2 text-[13px] font-bold text-zinc-950 hover:bg-white focus-visible:outline-2 focus-visible:outline-ember sm:px-3.5 sm:text-[14px] lg:ml-0">
          Open workspace
        </button>
      </div>
      <DesktopWarningDialog open={desktop.noticeOpen} remember={desktop.remember} onRememberChange={desktop.setRemember} onContinue={desktop.continueToWorkspace} onClose={desktop.closeNotice} />
    </header>
  );
}
