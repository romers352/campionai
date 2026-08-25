import React from "react";
import { motion } from "framer-motion";
import { Sparkles, X } from "lucide-react";

export default function CheckinBanner({ message, onUse, onDismiss }) {
  if (!message) return null;
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="glass-panel border border-border p-6 mb-8"
      data-testid="checkin-banner"
    >
      <div className="flex items-start gap-4">
        <Sparkles className="h-4 w-4 text-foreground/70 mt-1.5 shrink-0" strokeWidth={1.5} />
        <div className="flex-1">
          <p className="text-[10px] tracking-[0.25em] uppercase text-muted-foreground mb-2">CampionAI checked in</p>
          <p className="font-ai text-xl font-light leading-relaxed text-foreground">{message}</p>
          <div className="flex gap-3 mt-4">
            <button data-testid="checkin-reply-button" onClick={onUse}
              className="text-xs tracking-wide uppercase bg-primary text-primary-foreground rounded-full px-5 py-2 hover:bg-zinc-200 transition-colors">
              Reply
            </button>
            <button data-testid="checkin-dismiss-button" onClick={onDismiss}
              className="text-xs tracking-wide uppercase text-muted-foreground rounded-full px-4 py-2 hover:bg-accent transition-colors">
              Later
            </button>
          </div>
        </div>
        <button onClick={onDismiss} className="text-muted-foreground hover:text-foreground transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
    </motion.div>
  );
}
