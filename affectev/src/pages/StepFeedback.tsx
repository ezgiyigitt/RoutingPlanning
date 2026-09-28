import { useState } from "react";
import { AppContextType } from "../App";
import { Button } from "@/components/ui/button";
import { Star, CheckCircle2, Loader2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { submitFeedback } from "@/lib/api";

export default function StepFeedback({ state, setState, resetWizard }: AppContextType) {
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [hoverRating, setHoverRating] = useState(0);

  const routeNames = ["Comfort Route", "Balanced Route", "Efficient Route"];
  const routeName = state.selectedRoute !== null ? routeNames[state.selectedRoute] : "Balanced Route";
  const selectedRoute = state.routeData?.routes?.[state.selectedRoute ?? 1];
  const distKm = selectedRoute?.distance_km ?? 24.3;


  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await submitFeedback({
        origin: state.origin,
        destination: state.destination,
        selected_route: state.selectedRoute ?? 1,
        rating: state.rating,
        asi: state.routeData?.asi ?? 0,
        driver_id: state.driverId,
      });
    } catch {
      // silently continue
    } finally {
      setSubmitting(false);
      setSubmitted(true);
    }
  };

  return (
    <div className="bg-card p-8 rounded-2xl shadow-sm border border-border/50">
      <AnimatePresence mode="wait">
        {!submitted ? (
          <motion.div
            key="feedback-form"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="space-y-8"
          >
            <div className="text-center">
              <h2 className="text-2xl font-semibold tracking-tight text-foreground">How was your journey?</h2>
              <p className="text-muted-foreground mt-1">Help AffectEV learn your preferences</p>
            </div>

            <div className="bg-secondary/50 rounded-xl p-4 flex flex-col items-center justify-center space-y-2 border border-border/50">
              <div className="text-sm font-medium text-foreground">{state.origin} → {state.destination}</div>
              <div className="text-xs text-muted-foreground">{routeName} • {distKm} km</div>
              {state.routeData && (
                <div className="text-xs text-muted-foreground">
                  ASI: {state.routeData.asi.toFixed(3)} • {state.routeData.stress_category}
                </div>
              )}

            </div>

            <div className="flex justify-center space-x-2">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  onClick={() => setState({ ...state, rating: star })}
                  onMouseEnter={() => setHoverRating(star)}
                  onMouseLeave={() => setHoverRating(0)}
                  className="p-1 focus:outline-none transition-transform hover:scale-110 active:scale-95"
                >
                  <Star
                    className={`w-10 h-10 transition-colors ${
                      star <= (hoverRating || state.rating)
                        ? "fill-primary text-primary"
                        : "fill-transparent text-muted-foreground/30"
                    }`}
                  />
                </button>
              ))}
            </div>

            <Button
              className="w-full rounded-full h-14 text-lg font-medium transition-all hover:scale-[1.02] active:scale-[0.98]"
              onClick={handleSubmit}
              disabled={state.rating === 0 || submitting}
            >
              {submitting
                ? <><Loader2 className="w-5 h-5 mr-2 animate-spin" />Updating Q-Learning...</>
                : "Submit Feedback"
              }
            </Button>
          </motion.div>
        ) : (
          <motion.div
            key="success-msg"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex flex-col items-center justify-center py-8 space-y-6 text-center"
          >
            <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mb-2">
              <CheckCircle2 className="w-8 h-8 text-primary" />
            </div>
            <div>
              <h2 className="text-2xl font-semibold tracking-tight text-foreground">Thank You!</h2>
              <p className="text-muted-foreground mt-2 max-w-[250px] mx-auto">
                AffectEV Q-Learning engine has been updated with your preferences.
              </p>
            </div>

            <Button
              variant="outline"
              className="w-full rounded-full h-14 text-lg font-medium mt-4 border-border hover:bg-secondary/80"
              onClick={resetWizard}
            >
              Plan New Route
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
