import React, { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Play, Pause, RotateCcw } from "lucide-react";

// Box-breathing style guide: inhale → hold → exhale → hold (rest).
const PHASES = [
  { key: "inhale", label: "Breathe in", secs: 4, scale: 1.0 },
  { key: "hold", label: "Hold", secs: 4, scale: 1.0 },
  { key: "exhale", label: "Breathe out", secs: 6, scale: 0.55 },
  { key: "rest", label: "Rest", secs: 2, scale: 0.55 },
];

export default function BreathingPlayer() {
  const [running, setRunning] = useState(false);
  const [phaseIdx, setPhaseIdx] = useState(0);
  const [count, setCount] = useState(PHASES[0].secs);
  const [cycles, setCycles] = useState(0);
  const timer = useRef(null);

  useEffect(() => {
    if (!running) return undefined;
    timer.current = setInterval(() => {
      setCount((c) => {
        if (c > 1) return c - 1;
        // advance phase
        setPhaseIdx((pi) => {
          const next = (pi + 1) % PHASES.length;
          if (next === 0) setCycles((n) => n + 1);
          setCount(PHASES[next].secs);
          return next;
        });
        return PHASES[(phaseIdx + 1) % PHASES.length].secs;
      });
    }, 1000);
    return () => clearInterval(timer.current);
  }, [running, phaseIdx]);

  const reset = () => {
    setRunning(false);
    setPhaseIdx(0);
    setCount(PHASES[0].secs);
    setCycles(0);
  };

  const phase = PHASES[phaseIdx];
  const target = phase.key === "inhale" ? 1.0 : phase.key === "exhale" ? 0.55 : phase.scale;

  return (
    <div className="flex flex-col items-center py-6" data-testid="breathing-player">
      <div className="relative h-72 w-72 flex items-center justify-center">
        {/* soft glow rings */}
        <motion.div
          className="absolute rounded-full bg-foreground/[0.04] border border-border"
          style={{ height: "18rem", width: "18rem" }}
          animate={{ scale: running ? target : 0.75, opacity: running ? 1 : 0.5 }}
          transition={{ duration: running ? phase.secs : 0.6, ease: "easeInOut" }}
        />
        <motion.div
          className="absolute rounded-full bg-gradient-to-br from-white/[0.10] to-white/[0.02] border border-foreground/15"
          style={{ height: "12rem", width: "12rem" }}
          animate={{ scale: running ? target : 0.7 }}
          transition={{ duration: running ? phase.secs : 0.6, ease: "easeInOut" }}
        />
        <div className="relative text-center z-10">
          <p className="font-display font-light text-2xl tracking-tight" data-testid="breath-phase">{running ? phase.label : "Ready?"}</p>
          <p className="font-mono-data text-4xl mt-1 text-foreground/80">{running ? count : PHASES[0].secs}</p>
        </div>
      </div>

      <p className="text-sm text-muted-foreground mt-6 mb-6">
        {cycles > 0 ? `${cycles} cycle${cycles > 1 ? "s" : ""} · lovely.` : "Follow the circle. In for 4, hold, out for 6."}
      </p>

      <div className="flex items-center gap-3">
        <button
          onClick={() => setRunning((r) => !r)}
          data-testid="breath-toggle"
          className="h-14 w-14 rounded-full bg-primary text-primary-foreground hover:bg-zinc-200 flex items-center justify-center transition-colors"
        >
          {running ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5 ml-0.5" />}
        </button>
        <button
          onClick={reset}
          data-testid="breath-reset"
          className="h-11 w-11 rounded-full border border-border text-muted-foreground hover:text-foreground flex items-center justify-center transition-colors"
        >
          <RotateCcw className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
