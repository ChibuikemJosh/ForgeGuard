import { Link } from "react-router-dom";
import { NAV_LINKS } from "./data";

export function LandingNav() {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-coal/95">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-5">
        <Link to="/" className="flex items-center gap-2.5" aria-label="ForgeGuard home">
          <img src="/favicon.svg" alt="" className="size-7 self-center rounded-sm" />
          <span className="text-[19px] font-normal tracking-tight">ForgeGuard</span>
        </Link>
        <nav className="ml-auto hidden items-center gap-6 text-[15px] font-medium text-zinc-300 sm:flex" aria-label="Primary">
          {NAV_LINKS.map((item) => (
            <a key={item.href} href={item.href} className="hover:text-white focus-visible:outline-2 focus-visible:outline-ember">
              {item.label}
            </a>
          ))}
        </nav>
        <Link to="/workspace" className="ml-auto rounded-sm bg-zinc-100 px-3.5 py-2 text-[14px] font-bold text-zinc-950 hover:bg-white focus-visible:outline-2 focus-visible:outline-ember sm:ml-0">
          Open workspace
        </Link>
      </div>
    </header>
  );
}
