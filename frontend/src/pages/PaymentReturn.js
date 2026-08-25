import React, { useEffect, useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { CheckCircle2, XCircle, Loader2, Heart } from "lucide-react";

export function PaymentSuccess() {
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [state, setState] = useState("checking"); // checking | paid | donation | timeout
  const [type, setType] = useState(null);

  useEffect(() => {
    const sid = new URLSearchParams(window.location.search).get("session_id");
    if (!sid) { setState("timeout"); return; }
    let attempts = 0;
    const poll = async () => {
      attempts += 1;
      try {
        const { data } = await api.get(`/payments/status/${sid}`);
        setType(data.type);
        if (data.payment_status === "paid") {
          await refresh();
          setState(data.type === "donation" ? "donation" : "paid");
          return;
        }
      } catch {}
      if (attempts >= 6) { setState("timeout"); return; }
      setTimeout(poll, 2000);
    };
    poll();
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
        {state === "donation" && (
          <>
            <Heart className="h-12 w-12 text-primary mx-auto mb-6" strokeWidth={1.2} />
            <h1 className="font-display font-light text-4xl tracking-tight mb-3">Thank you, truly.</h1>
            <p className="text-muted-foreground mb-8">Your support helps keep CampionAI free for people who need it.</p>
            <Button className="rounded-full bg-primary text-primary-foreground hover:bg-zinc-200" onClick={() => navigate("/chat")}>Back to chat</Button>
          </>
        )}
        {state === "timeout" && (
          <>
            <p className="font-display font-light text-2xl mb-3">Still processing…</p>
            <p className="text-muted-foreground mb-8">This can take a moment. You can check your plan shortly.</p>
            <Button variant="outline" className="rounded-full border-border" onClick={() => navigate("/wellness")}>Go to Plus</Button>
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
