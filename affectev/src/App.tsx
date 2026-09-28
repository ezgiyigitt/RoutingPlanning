import { useState } from "react";
import { Switch, Route, Router as WouterRouter } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AnimatePresence, motion } from "framer-motion";

import StepPlanning from "./pages/StepPlanning";
import StepAnalysis from "./pages/StepAnalysis";
import StepResults from "./pages/StepResults";
import StepFeedback from "./pages/StepFeedback";
import ProgressBar from "./components/ProgressBar";
import type { RouteData } from "./lib/api";

const queryClient = new QueryClient();

export type AppState = {
  currentStep: number;
  origin: string;
  destination: string;
  battery: number;
  weather: string;
  traffic: string;

  driverId: string;
  
  // Kamera analizi sonuçları
  analysisResults: {
    cognitiveLoad: number;
    emotionalValence: number;
    fatigueIndex: number;
    smileRate: number;
    affectState: "Relaxed" | "Alert" | "Stressed" | "Fatigued" | null;
    // API'den gelen ek veriler
    smile_detected?: boolean;
    eyes_open?: boolean;
    emotion?: string;
    avg_ear?: number;
    eda_level?: number;
    pupil_dilation?: number;
    steering_variance?: number;
  } | null;

  // Rota planlama sonuçları (API'den)
  routeData: {
    asi: number;
    stress_category: string;
    routes: RouteData[];
    battery_constraints: {
      soc_min_percent: number;
      soc_max_percent: number;
      current_soc_percent: number;
      usable_energy_kwh: number;
    };
    recommended_breaks: { location: string; duration_min: number }[];
    route_diversity_info?: {
      physically_identical: boolean;
      distance_km: number;
      single_alternative_warning: boolean;
      note: string;
    };
    charging_points?: any[];
  } | null;

  selectedRoute: number | null;
  rating: number;
};

export type AppContextType = {
  state: AppState;
  setState: React.Dispatch<React.SetStateAction<AppState>>;
  nextStep: () => void;
  resetWizard: () => void;
};

function Wizard() {
  const [state, setState] = useState<AppState>({
    currentStep: 1,
    driverId: "U001",
    origin: "",
    destination: "",
    battery: 65,
    weather: "Sunny",
    traffic: "Moderate",
    analysisResults: null,
    routeData: null,
    selectedRoute: null,
    rating: 0,
  });

  const nextStep = () => {
    setState((prev) => ({ ...prev, currentStep: Math.min(prev.currentStep + 1, 4) }));
  };

  const resetWizard = () => {
    setState({
      currentStep: 1,
      driverId: "U001",
      origin: "",
      destination: "",
      battery: 65,
      weather: "Sunny",
      traffic: "Moderate",
      analysisResults: null,
      routeData: null,
      selectedRoute: null,
      rating: 0,
    });
  };

  const contextValue: AppContextType = { state, setState, nextStep, resetWizard };

  return (
    <div className="min-h-screen w-full bg-background flex flex-col items-center py-12 px-4 sm:px-6">
      <div className="w-full max-w-2xl relative">
        <ProgressBar currentStep={state.currentStep} totalSteps={4} />

        <div className="mt-8">
          <AnimatePresence mode="wait">
            <motion.div
              key={state.currentStep}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3, ease: "easeInOut" }}
            >
              {state.currentStep === 1 && <StepPlanning {...contextValue} />}
              {state.currentStep === 2 && <StepAnalysis {...contextValue} />}
              {state.currentStep === 3 && <StepResults {...contextValue} />}
              {state.currentStep === 4 && <StepFeedback {...contextValue} />}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

function Router() {
  return (
    <Switch>
      <Route path="/" component={Wizard} />
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
          <Router />
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
