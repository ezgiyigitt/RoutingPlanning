import { useEffect, useRef, useState } from "react";
import { api, type FaceResult } from "../lib/api";

const DURATION_MS = 3000;
const INTERVAL_MS = 200;

/** Satır içi kamera + 3 saniyelik yüz okuma. Sonucu onResult ile üst bileşene verir. */
export default function FaceCapture({ cognitive, onResult, onCameraError }: {
  cognitive: number; onResult: (r: FaceResult) => void; onCameraError?: (msg: string) => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [camErr, setCamErr] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [phase, setPhase] = useState<"idle" | "capturing" | "analyzing">("idle");
  const [progress, setProgress] = useState(0);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!navigator.mediaDevices?.getUserMedia) {
      const m = "Bu tarayıcı kamera erişimini desteklemiyor.";
      setCamErr(m); onCameraError?.(m);
      return;
    }
    navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: "user" }, audio: false })
      .then((s) => {
        if (cancelled) { s.getTracks().forEach((t) => t.stop()); return; }
        streamRef.current = s;
        const v = videoRef.current;
        if (v) { v.srcObject = s; v.onloadedmetadata = () => { v.play().catch(() => {}); setReady(true); }; }
      })
      .catch((e) => {
        const m = e?.name === "NotAllowedError" ? "Kamera izni verilmedi." : "Kamera açılamadı.";
        setCamErr(m); onCameraError?.(m);
      });
    return () => { cancelled = true; streamRef.current?.getTracks().forEach((t) => t.stop()); };
  }, []);

  async function start() {
    const v = videoRef.current;
    if (!v || !v.videoWidth) return;
    setErr(null); setPhase("capturing"); setProgress(0);
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
      setPhase("idle");
      if (!r.ok) { setErr(r.message ?? "Yüz bulunamadı."); return; }
      streamRef.current?.getTracks().forEach((t) => t.stop());
      onResult(r);
    } catch (e: any) { setErr(e.message); setPhase("idle"); }
  }

  const R = 46, C = 2 * Math.PI * R;
  return (
    <div>
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
      {err && <div className="face-err">{err}</div>}
      {!camErr && (
        <button className="btn-primary" disabled={!ready || phase !== "idle"} onClick={start}>
          {phase === "capturing" ? "Kameraya bakın…" : phase === "analyzing" ? "Analiz ediliyor…" : err ? "Tekrar dene" : "Yüz okumayı başlat (3 sn)"}
        </button>
      )}
    </div>
  );
}
