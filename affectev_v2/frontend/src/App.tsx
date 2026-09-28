import { useEffect, useState } from "react";
import Wizard from "./components/Wizard";

export default function App() {
  const sysDark = typeof window !== "undefined" && window.matchMedia?.("(prefers-color-scheme: dark)").matches;
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    try { return (localStorage.getItem("affectev-theme") as any) || (sysDark ? "dark" : "light"); } catch { return sysDark ? "dark" : "light"; }
  });
  const [toast, setToast] = useState<{ m: string; err?: boolean } | null>(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("affectev-theme", theme); } catch { /* */ }
  }, [theme]);
  useEffect(() => { if (toast) { const t = setTimeout(() => setToast(null), 2800); return () => clearTimeout(t); } }, [toast]);

  return (
    <>
      <header className="topbar">
        <div className="brand"><img src="/favicon.svg" alt="" />AffectEV</div>
        <button className="icon-btn" title="Görünüm" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
          {theme === "dark" ? "☀︎" : "☾"}
        </button>
      </header>
      <Wizard dark={theme === "dark"} onToast={(m, err) => setToast({ m, err })} />
      {toast && <div className={`toast ${toast.err ? "err" : ""}`}>{toast.m}</div>}
    </>
  );
}
