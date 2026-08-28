import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/sonner";
import AccountMenu from "@/components/AccountMenu";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { ArrowLeft, Loader2, CreditCard, AlertTriangle } from "lucide-react";

const fmtDate = (iso) => {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }); }
  catch { return "—"; }
};

const STATUS_COPY = {
  active: { label: "Active", tone: "text-foreground" },
  trialing: { label: "Free trial", tone: "text-foreground" },
  past_due: { label: "Payment failed", tone: "text-escalation" },
  cancelled: { label: "Cancelled", tone: "text-muted-foreground" },
  none: { label: "No plan", tone: "text-muted-foreground" },
};

export default function Billing() {
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const res = await api.get("/plus/billing");
      setData(res.data);
    } catch {
      toast.error("Couldn't load your billing details");
    }
  };
  useEffect(() => { load(); }, []);

  const cancel = async () => {
    setBusy(true);
    try {
      await api.post("/plus/cancel");
      await refresh();
      await load();
      toast.success("Cancelled. You keep Plus until your paid period ends.");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not cancel");
    } finally { setBusy(false); }
  };

  const resume = async () => {
    setBusy(true);
    try {
      await api.post("/plus/resume");
      await refresh();
      await load();
      toast.success("Your subscription is active again.");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not resume");
    } finally { setBusy(false); }
  };

  if (!data) {
    return <div className="min-h-screen bg-background flex items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  }

  const plus = data.plus || {};
  const status = STATUS_COPY[plus.status] || STATUS_COPY.none;
  // Local ledger + PayPal's own record, newest first. PayPal rows have no session_id.
  const rows = [
    ...(data.payments || []).map((p) => ({
      key: p.session_id, date: p.created_at, amount: p.amount,
      description: p.description || p.package_id, status: p.payment_status,
    })),
    ...(data.paypal_payments || []).map((p) => ({
      key: `pp-${p.id}`, date: p.date, amount: p.amount,
      description: p.description, status: (p.status || "").toLowerCase(),
    })),
  ].sort((a, b) => String(b.date || "").localeCompare(String(a.date || "")));

  return (
    <div className="min-h-screen bg-background">
      <header className="glass sticky top-0 z-20 h-16 flex items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" className="rounded-full" onClick={() => navigate("/chat")} data-testid="billing-back-button">
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <span className="font-display font-semibold text-xl tracking-tight">Billing</span>
        </div>
        <AccountMenu />
      </header>

      <div className="max-w-2xl mx-auto px-6 py-12">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>

          <div className="border border-border bg-card/40 rounded-2xl p-7 mb-8" data-testid="billing-plan-card">
            <div className="flex items-start justify-between gap-4 mb-6">
              <div>
                <p className="text-[10px] tracking-[0.3em] uppercase text-muted-foreground mb-2">Current plan</p>
                <p className="font-display font-light text-3xl tracking-tight">
                  {plus.active ? "CampionAI Plus" : "Free"}
                </p>
                <p className={`text-sm mt-1 ${status.tone}`} data-testid="billing-status">{status.label}</p>
              </div>
              <CreditCard className="h-5 w-5 text-muted-foreground shrink-0" strokeWidth={1.5} />
            </div>

            {plus.status === "past_due" && (
              <div className="flex items-start gap-3 rounded-xl border border-escalation/30 bg-escalation/5 p-4 mb-6" data-testid="billing-past-due">
                <AlertTriangle className="h-4 w-4 text-escalation mt-0.5 shrink-0" />
                <p className="text-sm text-foreground/85">
                  Your last payment didn't go through. Update your payment method in PayPal, then resume below.
                </p>
              </div>
            )}

            <dl className="space-y-3 text-sm mb-7">
              {plus.status === "trialing" ? (
                <div className="flex justify-between"><dt className="text-muted-foreground">Trial ends</dt><dd>{fmtDate(plus.trial_ends_at)}</dd></div>
              ) : (
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">{plus.cancel_at_period_end ? "Access until" : "Renews"}</dt>
                  <dd>{fmtDate(plus.until)}</dd>
                </div>
              )}
              {plus.plan_key && (
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Billing cycle</dt>
                  <dd>{plus.plan_key === "plus_yearly" ? "Yearly" : "Monthly"}</dd>
                </div>
              )}
            </dl>

            <div className="flex flex-wrap gap-3">
              {!plus.active && (
                <Button className="rounded-full bg-primary text-primary-foreground hover:bg-zinc-200" onClick={() => navigate("/wellness")} data-testid="billing-subscribe-button">
                  See plans
                </Button>
              )}
              {plus.status === "past_due" && (
                <Button variant="outline" className="rounded-full border-border" onClick={resume} disabled={busy} data-testid="billing-resume-button">
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Resume subscription"}
                </Button>
              )}
              {plus.has_subscription && !plus.cancel_at_period_end && plus.status !== "cancelled" && (
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button variant="outline" className="rounded-full border-border text-muted-foreground" data-testid="billing-cancel-button">
                      Cancel subscription
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Cancel your subscription?</AlertDialogTitle>
                      <AlertDialogDescription>
                        You'll keep Plus until {fmtDate(plus.until)}, then go back to the free plan.
                        Your conversations and memories stay exactly as they are.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel className="rounded-full" data-testid="billing-keep-plan">Keep Plus</AlertDialogCancel>
                      <AlertDialogAction onClick={cancel} className="rounded-full" data-testid="billing-confirm-cancel">Cancel subscription</AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              )}
            </div>
          </div>

          <p className="text-[10px] tracking-[0.3em] uppercase text-muted-foreground mb-4">Payment history</p>
          {rows.length === 0 ? (
            <p className="text-sm text-muted-foreground rounded-2xl border border-border bg-card/30 p-5" data-testid="billing-empty">
              No payments yet.
            </p>
          ) : (
            <div className="space-y-px bg-border border border-border rounded-2xl overflow-hidden" data-testid="billing-history">
              {rows.map((r) => (
                <div key={r.key} className="bg-card/60 flex items-center gap-4 p-4">
                  <span className="font-mono-data text-xs text-muted-foreground w-24 shrink-0">{fmtDate(r.date)}</span>
                  <p className="flex-1 text-sm truncate">{r.description}</p>
                  <span className="text-xs text-muted-foreground capitalize hidden sm:inline">{r.status}</span>
                  <span className="font-display font-light text-lg shrink-0">${Number(r.amount || 0).toFixed(2)}</span>
                </div>
              ))}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
