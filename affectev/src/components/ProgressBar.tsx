import { motion } from "framer-motion";

export default function ProgressBar({ currentStep, totalSteps }: { currentStep: number; totalSteps: number }) {
  return (
    <div className="flex justify-center items-center space-x-2">
      {Array.from({ length: totalSteps }).map((_, i) => {
        const stepNumber = i + 1;
        const isActive = stepNumber === currentStep;
        const isCompleted = stepNumber < currentStep;

        return (
          <div key={stepNumber} className="flex items-center">
            <motion.div
              className={`h-2 rounded-full transition-colors duration-300 ${
                isActive || isCompleted ? "bg-primary" : "bg-muted"
              }`}
              initial={false}
              animate={{
                width: isActive ? 32 : 8,
              }}
              transition={{ duration: 0.3 }}
            />
          </div>
        );
      })}
    </div>
  );
}
