import { useEffect, useRef, useState } from "react";
import { api, fmt, type FaceResult } from "../lib/api";

const DURATION_MS = 3000;
const INTERVAL_MS = 200;

export default function FaceReader({ cognitive, onApply, onClose }: {
  cognitive: number; onApply: (F: number, V: number) => void; onClose: () => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [camErr, setCamErr] = useState<string | null>(null);
  const [phase, setPhase] = useState<"idle" | "capturing" | "analyzing" | "done">("idle");
  const [progress, setProgress] = useState(0);
  const [res, setRes] = useState<FaceResult | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    navigator.mediaDevices?.getUserMedia({ video: { width: 640, height: 480, facingMode: "user" }, audio: false })
      .then((s) => {
        if (cancelled) { s.getTracks().forEach((t) => t.stop()); return; }
        streamRef.current = s;
        if (videoRef.current) { videoRef.current.srcObject = s; videoRef.current.play().catch(() => {}); }
      })
      .catch((e) => setCamErr(e?.name === "NotAllowedError" ? "Kamera izni verilmedi." : "Kamera açılamadı."));
    if (!navigator.mediaDevices) setCamErr("Bu tarayıcı kamera erişimini desteklemiyor.");
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    window.addEventListener("keydown", onKey);
    return () => { cancelled = true; streamRef.current?.getTracks().forEach((t) => t.stop()); window.removeEventListener("keydown", onKey); };
  }, []);

  function close() { streamRef.current?.getTracks().forEach((t) => t.stop()); onClose(); }

  async function start() {
    const v = videoRef.current;
    if (!v || !v.videoWidth) return;
    setErr(null); setRes(null); setPhase("capturing"); setProgress(0);
    const canvas = document.createElement("canvas");
    canvas.width = v.videoWidth; canvas.height = v.videoHeight;
    const ctx = canvas.getContext("2d")!;
    const frames: string[] = [];
    const t0 = performance.now();
    await new Promise<void>((resolve) => {
      const id = setInterval(() => {
        ctx.drawImage(v, 0, 0, canvas.width, canvas.height);
        frames.push(canvas.toDataURL("image/jpeg", 0.8));
        const p = (performance.now() - t0) / DURATION_MS;
        setProgress(Math.min(1, p));
        if (p >= 1) { clearInterval(id); resolve(); }
      }, INTERVAL_MS);
    });
    setPhase("analyzing");
    try {
      const r = await api.faceAnalyze(frames, cognitive);
      setRes(r); setPhase("done");
      if (!r.ok) setErr(r.message ?? "Yüz bulunamadı.");
    } catch (e: any) { setErr(e.message); setPhase("idle"); }
  }

  const R = 46, C = 2 * Math.PI * R;
  return (
    <div className="sheet-backdrop" onClick={close}>
      <div className="sheet" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-label="Yüz okuma">
        <div className="sheet-head">
          <div>
            <div className="sheet-title">Yüz Okuma</div>
            <div className="sheet-sub">3 saniyelik kamera analizi · Dn. 1'in F ve V girdilerini önerir</div>
          </div>
          <button className="icon-btn" onClick={close} aria-label="Kapat">✕</button>
        </div>

        <div className="cam">
          {camErr ? <div className="cam-msg">{camErr}</div> : <video ref={videoRef} muted playsInline />}
          {!camErr && <div className={`face-guide ${phase === "capturing" ? "live" : ""}`} />}
          {phase === "capturing" && (
            <svg className="ring" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r={R} stroke="rgba(255,255,255,.3)" strokeWidth="5" fill="none" />
              <circle cx="50" cy="50" r={R} stroke="#30d158" strokeWidth="5" fill="none" strokeLinecap="round"
                strokeDasharray={C} strokeDashoffset={C * (1 - progress)} transform="rotate(-90 50 50)" />
              <text x="50" y="58" textAnchor="middle" fontSize="26" fontWeight="700" fill="#fff">{Math.max(1, Math.ceil(3 - progress * 3))}</text>
            </svg>
          )}
          {phase === "analyzing" && <div className="cam-msg"><span className="spinner" /> Analiz ediliyor…</div>}
        </div>

        {res?.ok && (
          <div className="face-res">
            <div className="weight"><b>{fmt(res.fatigue!, 0)}</b><span>F · yorgunluk</span></div>
            <div className="weight"><b>{fmt(cognitive, 0)}</b><span>C · elle</span></div>
            <div className="weight"><b>{fmt(res.valence_negative!, 0)}</b><span>V · olumsuz değerlik</span></div>
            <div className="weight" style={{ background: "var(--accent)", color: "#fff" }}><b>{fmt(res.cls!, 1)}</b><span style={{ color: "rgba(255,255,255,.85)" }}>CLS · {res.state}</span></div>
          </div>
        )}
        {res?.ok && (
          <div className="face-detail">
            Gözler kapalı: %{fmt(100 * res.eyes_closed_ratio!, 0)} · Gülümseme: %{fmt(100 * res.smile_ratio!, 0)}
            {res.emotion_tr && <> · Baskın duygu: {res.emotion_tr}</>} · {res.face_frames}/{res.frames} karede yüz · {res.method}
          </div>
        )}
        {err && <div className="face-detail" style={{ color: "var(--red)" }}>{err}</div>}

        <div className="sheet-actions">
          {phase === "done" && res?.ok ? (
            <>
              <button className="btn-secondary" onClick={start}>Tekrar</button>
              <button className="btn-primary" style={{ margin: 0, width: "auto", padding: "0 22px", height: 42 }}
                onClick={() => { onApply(Math.round(res.fatigue!), Math.round(res.valence_negative!)); close(); }}>Değerleri uygula</button>
            </>
          ) : (
            <button className="btn-primary" style={{ margin: 0, height: 44 }} disabled={!!camErr || phase === "capturing" || phase === "analyzing"} onClick={start}>
              {phase === "capturing" ? "Kameraya bakın…" : "Analizi başlat"}
            </button>
          )}
        </div>
        <p className="note" style={{ margin: "10px 2px 0" }}>
          Deneysel modül: bildiride biyometrik kestirim kapsam dışıdır ve bu değerler doğrulanmamıştır.
          F = gözlerin kapalı olduğu kare oranı, V = olumsuz duygu olasılığı (model yoksa gülümsemeden).
          C kameradan ölçülmez; kaydırıcıdaki değer kullanılır. Görüntüler kaydedilmez, yalnızca yerel sunucuda işlenir.
        </p>
      </div>
    </div>
  );
}
