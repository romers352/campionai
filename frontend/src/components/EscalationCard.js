import React, { useState } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/sonner";
import { ShieldCheck, Phone, UserCheck, HeartHandshake, Video, Loader2 } from "lucide-react";

export default function EscalationCard({ escalation }) {
  const navigate = useNavigate();
  const [starting, setStarting] = useState(false);
  if (!escalation) return null;
  const {
    hotlines = [], trusted_contact, professional, message,
    trusted_contact_notified, professional_notified, consult_offer,
  } = escalation;

  // A crisis consult is free and uncapped — never gated on billing or the monthly limit.
  const startConsult = async () => {
    setStarting(true);
    try {
      const { data } = await api.post("/consults/request", {
        doctor_id: consult_offer.doctor_id, mode: "video", note: "Crisis support", crisis: true,
      });
      navigate(`/consult/${data.session.id}`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Couldn't connect you — please use a hotline above.");
      setStarting(false);
    }
  };
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

      {consult_offer && (
        <div className="mt-5 border border-escalation/30 bg-background p-5" data-testid="crisis-consult-offer">
          <div className="flex items-start gap-3 mb-4">
            <Video className="h-4 w-4 text-escalation mt-0.5 shrink-0" strokeWidth={1.5} />
            <div>
              <p className="text-sm font-medium leading-tight">Talk to {consult_offer.doctor_name} now</p>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                Free, right now{consult_offer.online_now ? " — they're online" : " — we'll ask them to join"}.
              </p>
            </div>
          </div>
          <Button className="w-full rounded-full bg-escalation hover:bg-escalation/90 gap-2"
            onClick={startConsult} disabled={starting} data-testid="start-crisis-consult">
            {starting ? <Loader2 className="h-4 w-4 animate-spin" /> : <><Video className="h-4 w-4" /> Connect me</>}
          </Button>
        </div>
      )}
    </motion.div>
  );
}
