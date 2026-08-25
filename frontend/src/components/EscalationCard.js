import React from "react";
import { motion } from "framer-motion";
import { ShieldCheck, Phone, UserCheck, HeartHandshake } from "lucide-react";

export default function EscalationCard({ escalation }) {
  if (!escalation) return null;
  const { hotlines = [], trusted_contact, professional, message } = escalation;
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="rounded-3xl border border-escalation/30 bg-escalation/[0.06] p-6 my-4"
      data-testid="escalation-card"
    >
      <div className="flex items-center gap-2.5 mb-4 text-escalation">
        <ShieldCheck className="h-5 w-5" />
        <span className="font-semibold font-display">You're not alone in this</span>
      </div>
      {message && <p className="text-sm text-foreground/90 leading-relaxed mb-5">{message}</p>}

      <div className="space-y-3">
        {hotlines.map((h, i) => (
          <div key={i} className="flex items-center justify-between rounded-2xl bg-card p-4 border border-border/60" data-testid={`hotline-${i}`}>
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-full bg-escalation/12 flex items-center justify-center">
                <Phone className="h-4 w-4 text-escalation" />
              </div>
              <div>
                <p className="text-sm font-medium leading-tight">{h.name}</p>
                <p className="text-xs text-muted-foreground">{h.hours}</p>
              </div>
            </div>
            <span className="text-sm font-semibold text-escalation">{h.number}</span>
          </div>
        ))}

        {trusted_contact && (
          <div className="flex items-center gap-3 rounded-2xl bg-card p-4 border border-border/60" data-testid="escalation-trusted-contact">
            <div className="h-9 w-9 rounded-full bg-primary/12 flex items-center justify-center">
              <HeartHandshake className="h-4 w-4 text-primary" />
            </div>
            <div>
              <p className="text-sm font-medium leading-tight">Trusted contact alerted: {trusted_contact.name}</p>
              <p className="text-xs text-muted-foreground capitalize">{trusted_contact.relationship}</p>
            </div>
          </div>
        )}

        {professional && (
          <div className="flex items-center gap-3 rounded-2xl bg-card p-4 border border-border/60" data-testid="escalation-professional">
            <div className="h-9 w-9 rounded-full bg-primary/12 flex items-center justify-center">
              <UserCheck className="h-4 w-4 text-primary" />
            </div>
            <div>
              <p className="text-sm font-medium leading-tight">Verified professional: {professional.name}</p>
              <p className="text-xs text-muted-foreground">{professional.specialty} · {professional.credentials}</p>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}
