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
      className="rounded-3xl bg-primary/[0.08] border border-primary/20 p-5 mb-4"
      data-testid="checkin-banner"
    >
      <div className="flex items-start gap-3">
        <div className="h-8 w-8 rounded-full bg-primary/15 flex items-center justify-center shrink-0">
          <Sparkles className="h-4 w-4 text-primary" />
        </div>
        <div className="flex-1">
          <p className="text-xs font-medium text-primary mb-1">CampionAI checked in</p>
          <p className="text-sm leading-relaxed text-foreground/90">{message}</p>
          <div className="flex gap-2 mt-3">
            <button data-testid="checkin-reply-button" onClick={onUse}
              className="text-xs font-medium bg-primary text-primary-foreground rounded-full px-4 py-1.5 hover:opacity-90 transition-opacity">
              Reply
            </button>
            <button data-testid="checkin-dismiss-button" onClick={onDismiss}
              className="text-xs font-medium text-muted-foreground rounded-full px-3 py-1.5 hover:bg-accent transition-colors">
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
