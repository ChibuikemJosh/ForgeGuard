import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";

const SKIP_KEY = "forge-skip-desktop-notice";

function shouldSkipNotice(): boolean {
  try {
    return window.localStorage.getItem(SKIP_KEY) === "1";
  } catch {
    return false;
  }
}

/**
 * Opens `/workspace` behind a desktop-first warning. Remembers the opt-out in
 * localStorage so repeat visitors go straight through.
 */
export function useDesktopWarning() {
  const navigate = useNavigate();
  const [noticeOpen, setNoticeOpen] = useState(false);
  const [remember, setRemember] = useState(false);

  const requestWorkspace = useCallback((e?: { preventDefault: () => void }) => {
    e?.preventDefault();
    if (shouldSkipNotice()) navigate("/workspace");
    else { setRemember(false); setNoticeOpen(true); }
  }, [navigate]);

  const closeNotice = useCallback(() => setNoticeOpen(false), []);

  const continueToWorkspace = useCallback(() => {
    try {
      if (remember) window.localStorage.setItem(SKIP_KEY, "1");
    } catch { /* private mode: just continue */ }
    setNoticeOpen(false);
    navigate("/workspace");
  }, [navigate, remember]);

  return { noticeOpen, remember, setRemember, requestWorkspace, closeNotice, continueToWorkspace };
}
