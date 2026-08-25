import React from "react";
import { motion } from "framer-motion";
import { ShieldCheck, Phone, UserCheck, HeartHandshake } from "lucide-react";

export default function EscalationCard({ escalation }) {
  if (!escalation) return null;
  const { hotlines = [], trusted_contact, professional, message, trusted_contact_notified, professional_notified } = escalation;
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="border border-escalation/40 bg-escalation/[0.06] p-7 my-6"
      data-testid="escalation-card"
    >
      <div className="flex items-center gap-2.5 mb-5 text-escalation">
        <ShieldCheck className="h-5 w-5" strokeWidth={1.5} />
        <span className="text-[10px] tracking-[0.25em] uppercase font-medium">You're not alone in this</span>
      </div>
      {message && <p className="font-ai text-lg font-light text-foreground leading-relaxed mb-6">{message}</p>}

      <div className="space-y-px bg-border">
        {hotlines.map((h, i) => (
          <div key={i} className="flex items-center justify-between bg-background p-4" data-testid={`hotline-${i}`}>
            <div className="flex items-center gap-3">
              <Phone className="h-4 w-4 text-escalation" strokeWidth={1.5} />
              <div>
                <p className="text-sm font-medium leading-tight">{h.name}</p>
                <p className="text-[11px] text-muted-foreground font-mono-data">{h.hours}</p>
              </div>
            </div>
            <span className="text-sm font-medium text-escalation font-mono-data">{h.number}</span>
          </div>
        ))}
        {trusted_contact && (
          <div className="flex items-center gap-3 bg-background p-4" data-testid="escalation-trusted-contact">
            <HeartHandshake className="h-4 w-4 text-muted-foreground" strokeWidth={1.5} />
            <div>
              <p className="text-sm font-medium leading-tight">
                {trusted_contact_notified ? `Trusted contact alerted — ${trusted_contact.name}` : `Trusted contact on file — ${trusted_contact.name}`}
              </p>
              <p className="text-[11px] text-muted-foreground">
                {trusted_contact_notified ? <span className="capitalize">{trusted_contact.relationship}</span> : <><span className="capitalize">{trusted_contact.relationship}</span> · reach out to them directly if you can</>}
              </p>
            </div>
          </div>
        )}
        {professional && (
          <div className="flex items-center gap-3 bg-background p-4" data-testid="escalation-professional">
            <UserCheck className="h-4 w-4 text-muted-foreground" strokeWidth={1.5} />
            <div>
              <p className="text-sm font-medium leading-tight">
                {professional_notified ? `Verified professional notified — ${professional.name}` : `Verified professional — ${professional.name}`}
              </p>
              <p className="text-[11px] text-muted-foreground">{professional.specialty} · {professional.credentials}</p>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}
