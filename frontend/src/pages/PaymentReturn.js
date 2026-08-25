import React, { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";

/**
 * PayPal Buttons complete in-page, so these are landing pages for the redirect
 * flows only (and anyone who bookmarks them). The webhook is what actually grants
 * access — here we just re-read our own state until it lands.
 */
export function PaymentSuccess() {
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [state, setState] = useState("checking"); // checking | paid | pending

  useEffect(() => {
    let cancelled = false;
    let attempts = 0;
    const poll = async () => {
      attempts += 1;
      try {
        const { data } = await api.get("/plus/status");
        if (cancelled) return;
        if (data.active) {
          await refresh();
          setState("paid");
          return;
        }
      } catch { /* keep polling */ }
      if (cancelled) return;
      if (attempts >= 6) { setState("pending"); return; }
      setTimeout(poll, 2000);
    };
    poll();
    return () => { cancelled = true; };
  }, [refresh]);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="max-w-md text-center" data-testid="payment-success">
        {state === "checking" && (
          <>
            <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-6" />
            <p className="font-display font-light text-2xl">Confirming your payment…</p>
          </>
        )}
        {state === "paid" && (
          <>
            <CheckCircle2 className="h-12 w-12 text-primary mx-auto mb-6" strokeWidth={1.2} />
            <h1 className="font-display font-light text-4xl tracking-tight mb-3">Welcome to Plus.</h1>
            <p className="text-muted-foreground mb-8">Your companion is ready to coach you. Let's build today's plan.</p>
            <Button className="rounded-full bg-primary text-primary-foreground hover:bg-zinc-200" onClick={() => navigate("/wellness")} data-testid="go-wellness-button">Open my plan</Button>
          </>
        )}
        {state === "pending" && (
          <>
            <p className="font-display font-light text-2xl mb-3">Still processing…</p>
            <p className="text-muted-foreground mb-8">PayPal can take a moment to confirm. Your plan will unlock automatically.</p>
            <Button variant="outline" className="rounded-full border-border" onClick={() => navigate("/billing")}>Check billing</Button>
          </>
        )}
      </motion.div>
    </div>
  );
}

export function PaymentCancel() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6">
      <div className="max-w-md text-center" data-testid="payment-cancel">
        <XCircle className="h-12 w-12 text-muted-foreground mx-auto mb-6" strokeWidth={1.2} />
        <h1 className="font-display font-light text-4xl tracking-tight mb-3">No worries.</h1>
        <p className="text-muted-foreground mb-8">Checkout was cancelled — nothing was charged.</p>
        <Link to="/wellness"><Button variant="outline" className="rounded-full border-border">Back to Plus</Button></Link>
      </div>
    </div>
  );
}
