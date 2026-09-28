import { useEffect, useState, useRef } from "react";
import { AppContextType } from "../App";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { ScanFace, Wifi, WifiOff } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { analyzeEmotion, planRoute } from "@/lib/api";

export default function StepAnalysis({ state, setState, nextStep }: AppContextType) {
  const [phase, setPhase] = useState<"countdown" | "analyzing" | "routing" | "complete">("countdown");
  const [countdown, setCountdown] = useState(3);
  const [apiStatus, setApiStatus] = useState<"live" | "sim">("sim");
  const [errorMsg, setErrorMsg] = useState("");

  const [metrics, setMetrics] = useState({
    cognitiveLoad: 0,
    emotionalValence: 0,
    fatigueIndex: 0,
    smileRate: 0,
  });

  const videoRef = useRef<HTMLVideoElement>(null);

  // Real camera → base64 → API analysis
  const runCameraAnalysis = async (): Promise<{
    smile_detected: boolean;
    eyes_open: boolean;
    emotion: string;
    avg_ear: number;
  }> => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      const video = videoRef.current;
      if (!video) throw new Error("Video ref not found");
      
      video.srcObject = stream;
      await video.play();

      await new Promise(r => setTimeout(r, 500)); // camera warm-up

      const canvas = document.createElement("canvas");
      canvas.width = 320; canvas.height = 240;
      const ctx = canvas.getContext("2d")!;

      const results: Awaited<ReturnType<typeof analyzeEmotion>>[] = [];

      for (let i = 0; i < 5; i++) {
        if (!video || video.paused || video.ended) break;
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const b64 = canvas.toDataURL("image/jpeg", 0.8).split(",")[1];
        try {
          const r = await analyzeEmotion(b64);
          results.push(r);
        } catch { /* skip frame */ }
        await new Promise(r => setTimeout(r, 400));
      }

      stream.getTracks().forEach(t => t.stop());

      if (results.length === 0) throw new Error("no frames");

      setApiStatus("live");
      const smileCount = results.filter(r => r.smile_detected).length;
      const eyesCount = results.filter(r => r.eyes_open).length;
      const avgEar = results.reduce((s, r) => s + r.avg_ear, 0) / results.length;
      
      let emotions = results.map(r => r.emotion).filter(e => e !== "unknown");
      let topEmotion = emotions.length > 0 
        ? emotions.sort((a, b) => emotions.filter(e => e === b).length - emotions.filter(e => e === a).length)[0]
        : "unknown";

      const finalSmile = smileCount >= 2;
      const finalEyes = eyesCount >= 3;

      if (topEmotion === "unknown") {
        if (finalSmile) topEmotion = "happiness";
        else if (!finalEyes) topEmotion = "fatigued";
        else topEmotion = "neutral";
      }

      return {
        smile_detected: finalSmile,
        eyes_open: finalEyes,
        emotion: topEmotion,
        avg_ear: avgEar,
      };
    } catch {
      // No camera or API offline → simulation
      return {
        smile_detected: Math.random() > 0.5,
        eyes_open: Math.random() > 0.3,
        emotion: ["happiness", "neutral", "sadness"][Math.floor(Math.random() * 3)],
        avg_ear: 0.22 + Math.random() * 0.1,
      };
    }
  };

  useEffect(() => {
    if (phase === "countdown") {
      const timer = setInterval(() => {
        setCountdown(c => {
          if (c <= 1) {
            clearInterval(timer);
            setPhase("analyzing");
            return 0;
          }
          return c - 1;
        });
      }, 1000);
      return () => clearInterval(timer);
    }

    if (phase === "analyzing") {
      // Perform camera analysis, show metric animation simultaneously
      // Metrics will be determined by emotion after camera result
      // Only placeholder here (for animation)
      const placeholderMetrics = { cognitiveLoad: 50, emotionalValence: 50, fatigueIndex: 30, smileRate: 50 };

      let progress = 0;
      let cameraResult: Awaited<ReturnType<typeof runCameraAnalysis>> | null = null;
      const cameraPromise = runCameraAnalysis().then(r => { cameraResult = r; });

      const interval = setInterval(() => {
        progress += 5;
        setMetrics({
          cognitiveLoad:    placeholderMetrics.cognitiveLoad    * (progress / 100),
          emotionalValence: placeholderMetrics.emotionalValence * (progress / 100),
          fatigueIndex:     placeholderMetrics.fatigueIndex     * (progress / 100),
          smileRate:        placeholderMetrics.smileRate        * (progress / 100),
        });

        if (progress >= 100) {
          clearInterval(interval);
          // Wait for camera to finish then continue
          cameraPromise.then(() => {
            const cam = cameraResult;
            const emotion  = cam?.emotion ?? "neutral";
            const eyesOpen = cam?.eyes_open ?? true;

            // Realistic metric values based on emotion
            let cognitiveLoad: number, emotionalValence: number;
            let fatigueIndex: number, smileRate: number;
            let pupilDilation: number, edaLevel: number;

            if (emotion === "fear" || emotion === "anger") {
              cognitiveLoad    = 80 + Math.random() * 15;
              emotionalValence = 15 + Math.random() * 15;
              fatigueIndex     = 60 + Math.random() * 20;
              smileRate        = 5  + Math.random() * 10;
              pupilDilation    = 55 + Math.random() * 10;
              edaLevel         = 0.75 + Math.random() * 0.2;
            } else if (emotion === "sadness" || emotion === "disgust") {
              cognitiveLoad    = 55 + Math.random() * 20;
              emotionalValence = 20 + Math.random() * 20;
              fatigueIndex     = 50 + Math.random() * 20;
              smileRate        = 10 + Math.random() * 15;
              pupilDilation    = 42 + Math.random() * 8;
              edaLevel         = 0.5 + Math.random() * 0.2;
            } else if (emotion === "happiness" || emotion === "surprise") {
              cognitiveLoad    = 20 + Math.random() * 20;
              emotionalValence = 70 + Math.random() * 25;
              fatigueIndex     = 10 + Math.random() * 20;
              smileRate        = 70 + Math.random() * 25;
              pupilDilation    = 30 + Math.random() * 8;
              edaLevel         = 0.2 + Math.random() * 0.1;
            } else {
              cognitiveLoad    = 30 + Math.random() * 25;
              emotionalValence = 45 + Math.random() * 20;
              fatigueIndex     = 25 + Math.random() * 20;
              smileRate        = 40 + Math.random() * 20;
              pupilDilation    = 35 + Math.random() * 8;
              edaLevel         = 0.3 + Math.random() * 0.1;
            }

            if (!eyesOpen) {
              fatigueIndex  = Math.min(100, fatigueIndex + 20);
              cognitiveLoad = Math.min(100, cognitiveLoad + 10);
            }

            const finalMetrics = {
              cognitiveLoad:    Math.round(cognitiveLoad),
              emotionalValence: Math.round(emotionalValence),
              fatigueIndex:     Math.round(fatigueIndex),
              smileRate:        Math.round(smileRate),
            };
            setMetrics(finalMetrics);

            // affectState: derived from emotion + metrics together
            let affectState: "Relaxed" | "Alert" | "Stressed" | "Fatigued" = "Relaxed";
            if (emotion === "fear" || emotion === "anger" || finalMetrics.cognitiveLoad > 65) {
              affectState = "Stressed";
            } else if (!eyesOpen || finalMetrics.fatigueIndex > 55) {
              affectState = "Fatigued";
            } else if (emotion === "happiness" || finalMetrics.emotionalValence > 65) {
              affectState = "Alert";
            }

            setState(s => ({
              ...s,
              analysisResults: {
                ...finalMetrics,
                affectState,
                smile_detected: cam?.smile_detected,
                eyes_open:      cam?.eyes_open,
                emotion:        cam?.emotion,
                avg_ear:        cam?.avg_ear,
                eda_level:         edaLevel,
                pupil_dilation:    pupilDilation,
                steering_variance: finalMetrics.cognitiveLoad * 0.5,
              }
            }));
            setPhase("routing");
          });
        }
      }, 100);
      return () => clearInterval(interval);
    }

    if (phase === "routing") {
      // Calculate route (API)
      const a = state.analysisResults;
      planRoute({
        origin: state.origin,
        destination: state.destination,
        battery: state.battery,
        weather: state.weather,
        traffic: state.traffic,
        pupil_dilation: a?.pupil_dilation ?? 35,
        steering_variance: a?.steering_variance ?? 20,
        eda_level: a?.eda_level ?? 0.3,
        smile_ratio: a?.smileRate ? a.smileRate / 100 : 0.3,
        eyes_tired: a?.eyes_open === false,
        driver_id: state.driverId,
        affect_state: a?.affectState ?? undefined,
        emotion: a?.emotion ?? undefined,
      }).then(routeData => {
        setState(s => ({ ...s, routeData }));
        setPhase("complete");
      }).catch(e => {
        setErrorMsg("Could not connect to API, using simulation mode.");
        // Continue with empty data for simulation
        setState(s => ({ ...s, routeData: null }));
        setPhase("complete");
      });
    }
  }, [phase, setState, state.origin, state.destination, state.battery, state.weather, state.traffic, state.analysisResults]);

  return (
    <div className="bg-card p-8 rounded-2xl shadow-sm border border-border/50">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-semibold tracking-tight text-foreground">Driver Analysis</h2>
        <p className="text-muted-foreground mt-1">AI is reading your biometric state</p>
      </div>

      <div className="flex flex-col items-center space-y-8">
        {/* API Status */}
        <div className="flex items-center space-x-2 text-xs text-muted-foreground">
          {apiStatus === "live"
            ? <><Wifi className="w-3 h-3 text-green-500" /><span className="text-green-600">Live AI Engine</span></>
            : <><WifiOff className="w-3 h-3 text-orange-500" /><span className="text-orange-600">Simulation Mode</span></>
          }
        </div>

        {/* Camera Viewfinder */}
        <div className="relative w-48 h-48 bg-[#1C1C1E] rounded-2xl flex items-center justify-center overflow-hidden border border-[#2C2C2E]">
          <video
            ref={videoRef}
            className="absolute inset-0 w-full h-full object-cover scale-x-[-1]"
            playsInline
            muted
          />
          {phase === "countdown" && <ScanFace className="w-24 h-24 text-white/20 absolute z-10" strokeWidth={1} />}

          <AnimatePresence>
            {phase === "countdown" && (
              <motion.div
                key="countdown"
                initial={{ scale: 0.5, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 1.5, opacity: 0 }}
                className="absolute inset-0 flex flex-col items-center justify-center text-white"
              >
                <span className="text-5xl font-bold">{countdown}</span>
                <span className="text-xs mt-2 opacity-60">Get ready</span>
              </motion.div>
            )}

            {(phase === "analyzing" || phase === "routing") && (
              <motion.div
                key="analyzing"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="absolute inset-0 flex items-center justify-center text-white"
              >
                <div className="absolute inset-0 border-4 border-primary rounded-2xl animate-pulse opacity-50" />
                <span className="text-sm font-medium tracking-widest uppercase">
                  {phase === "routing" ? "Planning Route" : "Analyzing"}
                </span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Metrics */}
        <div className="w-full space-y-4 max-w-sm">
          <MetricBar label="Cognitive Load" value={metrics.cognitiveLoad} color="bg-blue-500" />
          <MetricBar label="Emotional Valence" value={metrics.emotionalValence} color="bg-purple-500" />
          <MetricBar label="Fatigue Index" value={metrics.fatigueIndex} color="bg-orange-500" />
          <MetricBar label="Smile Rate" value={metrics.smileRate} color="bg-green-500" />
        </div>

        {/* Error */}
        {errorMsg && (
          <p className="text-xs text-orange-500 text-center max-w-sm">{errorMsg}</p>
        )}

        {/* Result & Next Button */}
        <div className="h-24 flex flex-col items-center justify-end w-full">
          <AnimatePresence>
            {phase === "complete" && state.analysisResults && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full flex flex-col items-center space-y-4"
              >
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-medium text-muted-foreground">Detected State:</span>
                    <Badge variant="secondary" className="px-3 py-1 text-sm bg-primary/10 text-primary border-primary/20">
                      {state.analysisResults.affectState}
                    </Badge>
                  </div>
                  {state.analysisResults.emotion && (
                    <div className="flex items-center space-x-2">
                      <span className="text-sm font-medium text-muted-foreground">Emotion:</span>
                      <Badge variant="outline" className="px-2 py-0.5 text-xs">
                        {state.analysisResults.emotion}
                      </Badge>
                    </div>
                  )}
                </div>
                <Button
                  className="w-full rounded-full h-14 text-lg font-medium transition-all hover:scale-[1.02] active:scale-[0.98]"
                  onClick={nextStep}
                >
                  View Recommended Routes
                </Button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

function MetricBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-sm">
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${color}`} />
          <span className="text-foreground font-medium">{label}</span>
        </div>
        <span className="text-muted-foreground font-mono">{Math.round(value)}%</span>
      </div>
      <Progress value={value} className="h-1.5" />
    </div>
  );
}
