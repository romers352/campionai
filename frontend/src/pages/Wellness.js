import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "@/components/ui/sonner";
import PayPalSubscribe, { paypalConfigured } from "@/components/PayPalSubscribe";
import {
  ArrowLeft, Sparkles, Check, RefreshCw, Utensils, CalendarClock, Plus, Trash2,
  Wind, Flower2, Activity, Brain, HeartHandshake, Loader2, Heart,
} from "lucide-react";

const TYPE_ICON = { breathing: Wind, yoga: Flower2, movement: Activity, meditation: Brain, task: HeartHandshake };
const MACRO_TARGETS = { protein_g: 120, carbs_g: 250, fat_g: 70 };
const CAL_GOAL = 2000;

const Glow = () => (
  <div className="pointer-events-none fixed inset-0 z-0" aria-hidden
    style={{ background: "radial-gradient(700px circle at 50% -15%, rgba(255,255,255,0.07), transparent 55%)" }} />
);

/* -------- Paywall -------- */
const INCLUDED = [
  { icon: Brain, label: "AI daily plan", note: "Meditation, yoga & breathing tuned to your goals" },
  { icon: HeartHandshake, label: "Real-life tasks", note: "Gentle nudges that fit your actual day" },
  { icon: Utensils, label: "Effortless food log", note: "Describe a meal, we estimate the macros" },
  { icon: CalendarClock, label: "Gentle schedule", note: "Give your intentions a time that sticks" },
];
const PLAN_PERKS = [
  "Personalized plan, refreshed daily",
  "Natural-language calorie & macro tracking",
  "Proactive coaching woven into every chat",
  "Cancel anytime — your data stays yours",
];

function Paywall({ status, onTrial, onCheckout, onDonate, onActivated, busy }) {
  const [donors, setDonors] = useState([]);
  const [custom, setCustom] = useState("");
  const [anon, setAnon] = useState(false);
  useEffect(() => { api.get("/donors/top").then(({ data }) => setDonors(data)).catch(() => {}); }, []);
  const donateCustom = () => {
    const amt = parseFloat(custom);
    if (!amt || amt < 1) { toast.error("Enter an amount of at least $1"); return; }
    onCheckout("donate_custom", { amount: amt, anonymous: anon });
  };
  const plans = [
    { id: "plus_monthly", price: "$9", per: "/mo", note: "Billed monthly" },
    { id: "plus_yearly", price: "$86.40", per: "/yr", note: "Just $7.20/mo · billed yearly", featured: true, save: "Save 20%" },
  ];
  return (
    <div className="relative z-10 max-w-3xl mx-auto px-6 py-16 md:py-20">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}>
        <p className="text-[10px] tracking-[0.3em] uppercase text-muted-foreground mb-5 flex items-center gap-2"><Sparkles className="h-3.5 w-3.5" /> CampionAI Plus</p>
        <h1 className="font-display font-light text-4xl md:text-6xl tracking-tight leading-[1.02] mb-5">
          Your companion becomes<br /><span className="italic">your daily coach.</span>
        </h1>
        <p className="text-muted-foreground text-lg leading-relaxed mb-12 max-w-xl">
          A gentle, personal wellness rhythm — and CampionAI weaves it into your conversations, so it feels
          less like an app and more like a friend cheering you on.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-px bg-border border border-border rounded-2xl overflow-hidden mb-14">
          {INCLUDED.map((f) => (
            <div key={f.label} className="bg-card/60 p-6 flex items-start gap-4">
              <div className="h-10 w-10 rounded-xl bg-white/[0.04] border border-border flex items-center justify-center shrink-0">
                <f.icon className="h-5 w-5 text-foreground/80" strokeWidth={1.5} />
              </div>
              <div>
                <p className="font-medium">{f.label}</p>
                <p className="text-sm text-muted-foreground leading-relaxed">{f.note}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 mb-6">
          {plans.map((p) => (
            <div key={p.id}
              className={`relative p-8 rounded-2xl transition-colors ${p.featured ? "border border-foreground bg-white/[0.04] ambient-shadow-lg" : "border border-border bg-card/40 hover:border-foreground/40"}`}
              data-testid={`plan-${p.id}`}>
              {p.save && <span className="absolute -top-3 left-8 bg-primary text-primary-foreground text-[10px] tracking-[0.15em] uppercase px-3 py-1 rounded-full">{p.save}</span>}
              <div className="flex items-end gap-1.5 mb-1">
                <span className="font-display font-light text-5xl leading-none">{p.price}</span>
                <span className="text-muted-foreground mb-1.5">{p.per}</span>
              </div>
              <p className="text-xs text-muted-foreground mb-6">{p.note}</p>
              {p.featured && (
                <ul className="space-y-2.5 mb-7">
                  {PLAN_PERKS.map((perk) => (
                    <li key={perk} className="flex items-start gap-2.5 text-sm text-foreground/85">
                      <Check className="h-4 w-4 text-foreground/70 mt-0.5 shrink-0" strokeWidth={2} /> {perk}
                    </li>
                  ))}
                </ul>
              )}
              <Button className={`w-full rounded-full ${p.featured ? "bg-primary text-primary-foreground hover:bg-zinc-200" : "bg-transparent border border-border text-foreground hover:bg-accent"}`}
                onClick={() => onCheckout(p.id)} disabled={busy} data-testid={`subscribe-${p.id}`}>
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : `Choose ${p.featured ? "yearly" : "monthly"}`}
              </Button>
            </div>
          ))}
        </div>
        <p className="text-center text-xs text-muted-foreground mb-14">Every plan starts with a 14-day free trial. No charge today.</p>

        {paypalConfigured() && (
          <div className="mb-14">
            <div className="flex items-center gap-4 mb-6">
              <div className="h-px flex-1 bg-border" />
              <span className="text-[10px] tracking-[0.3em] uppercase text-muted-foreground">Or subscribe with PayPal</span>
              <div className="h-px flex-1 bg-border" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="border border-border rounded-2xl bg-card/40 p-5">
                <p className="text-sm text-muted-foreground mb-4">Monthly · $9/mo</p>
                <PayPalSubscribe planKey="monthly" onActivated={onActivated} />
              </div>
              <div className="border border-border rounded-2xl bg-card/40 p-5">
                <p className="text-sm text-muted-foreground mb-4">Yearly · $86.40/yr</p>
                <PayPalSubscribe planKey="yearly" onActivated={onActivated} />
              </div>
            </div>
          </div>
        )}

        {!status.trial_used && (
          <div className="border border-border bg-card/40 rounded-2xl p-7 flex flex-col sm:flex-row sm:items-center justify-between gap-5 mb-16">
            <div className="flex items-start gap-4">
              <Sparkles className="h-5 w-5 text-foreground/70 mt-0.5 shrink-0" strokeWidth={1.5} />
              <div>
                <p className="font-medium">Not ready to commit?</p>
                <p className="text-sm text-muted-foreground">Try everything free for 14 days — no card needed.</p>
              </div>
            </div>
            <Button variant="outline" className="rounded-full border-foreground/30 hover:bg-accent shrink-0" onClick={onTrial} disabled={busy} data-testid="start-trial-button">
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Start 14-day free trial"}
            </Button>
          </div>
        )}

        <div className="border-t border-border pt-12">
          <p className="text-[10px] tracking-[0.3em] uppercase text-muted-foreground mb-3 flex items-center gap-2"><Heart className="h-3.5 w-3.5" /> Keep CampionAI free for everyone</p>
          <p className="text-muted-foreground mb-6 max-w-lg leading-relaxed">
            CampionAI is free for individuals — and always will be. If Plus isn't for you but you'd like to help,
            any amount keeps the lights on for people who need it.
          </p>

          <div className="flex flex-wrap gap-2 mb-4">
            {[["donate_5", "$5"], ["donate_15", "$15"], ["donate_30", "$30"]].map(([id, label]) => (
              <Button key={id} variant="outline" className="rounded-full border-border hover:border-foreground/40 hover:bg-accent px-5" onClick={() => onDonate(id)} disabled={busy} data-testid={`donate-${id}`}>
                {label}
              </Button>
            ))}
          </div>

          <div className="flex gap-2 max-w-sm mb-3">
            <div className="relative flex-1">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
              <Input type="number" min="1" step="1" className="rounded-full h-11 pl-7" placeholder="Custom amount" value={custom}
                onChange={(e) => setCustom(e.target.value)} onKeyDown={(e) => e.key === "Enter" && donateCustom()} data-testid="custom-donate-input" />
            </div>
            <Button className="rounded-full bg-primary text-primary-foreground hover:bg-zinc-200 px-6" onClick={donateCustom} disabled={busy} data-testid="custom-donate-button">
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Donate"}
            </Button>
          </div>
          <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer mb-12">
            <Checkbox checked={anon} onCheckedChange={(v) => setAnon(!!v)} data-testid="donate-anonymous-checkbox" />
            Donate anonymously (won't appear on the supporters list)
          </label>

          {donors.length > 0 && (
            <div>
              <p className="text-[10px] tracking-[0.3em] uppercase text-muted-foreground mb-5">Top supporters</p>
              <div className="space-y-px bg-border border border-border rounded-2xl overflow-hidden" data-testid="top-donors">
                {donors.map((d, i) => (
                  <div key={i} className="bg-card/60 flex items-center gap-4 p-4" data-testid={`donor-${i}`}>
                    <span className="font-mono-data text-sm text-muted-foreground w-5 shrink-0">{i + 1}</span>
                    <img src={d.avatar} alt="" className="h-9 w-9 rounded-full border border-border shrink-0" />
                    <p className="flex-1 text-sm font-medium truncate">{d.name}</p>
                    <span className="font-display font-light text-lg shrink-0">${d.total}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}

/* -------- Calorie ring -------- */
function CalorieRing({ value }) {
  const r = 46, c = 2 * Math.PI * r;
  const pct = Math.min(1, value / CAL_GOAL);
  return (
    <div className="relative h-40 w-40 shrink-0">
      <svg viewBox="0 0 110 110" className="h-40 w-40 -rotate-90">
        <circle cx="55" cy="55" r={r} fill="none" stroke="hsl(var(--border))" strokeWidth="7" />
        <motion.circle cx="55" cy="55" r={r} fill="none" stroke="hsl(var(--foreground))" strokeWidth="7" strokeLinecap="round"
          strokeDasharray={c} initial={{ strokeDashoffset: c }} animate={{ strokeDashoffset: c * (1 - pct) }} transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display font-light text-4xl leading-none">{value}</span>
        <span className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground mt-1">of {CAL_GOAL} kcal</span>
      </div>
    </div>
  );
}

function MacroBar({ label, value, target }) {
  const pct = Math.min(100, Math.round((value / target) * 100));
  return (
    <div>
      <div className="flex justify-between text-sm mb-1.5">
        <span className="text-foreground/80">{label}</span>
        <span className="font-mono-data text-muted-foreground">{value}g</span>
      </div>
      <div className="h-1.5 rounded-full bg-border overflow-hidden">
        <motion.div className="h-full bg-foreground/70 rounded-full" initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }} />
      </div>
    </div>
  );
}

export default function Wellness() {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const [status, setStatus] = useState(user?.plus || { active: false, trial_used: false });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [plan, setPlan] = useState(null);
  const [food, setFood] = useState({ logs: [], totals: {} });
  const [foodText, setFoodText] = useState("");
  const [events, setEvents] = useState([]);
  const [evtTitle, setEvtTitle] = useState("");
  const [evtTime, setEvtTime] = useState("09:00");

  const name = user?.profile?.preferred_name || "friend";

  const loadStatus = async () => {
    const { data } = await api.get("/plus/status");
    setStatus(data); setLoading(false); return data;
  };
  const loadPlusData = async () => {
    const today = new Date().toISOString().slice(0, 10);
    try {
      const [p, f, e] = await Promise.all([
        api.get("/wellness/plan"), api.get("/wellness/food"), api.get(`/wellness/events?date=${today}`),
      ]);
      setPlan(p.data); setFood(f.data); setEvents(e.data);
    } catch {
      toast.error("Couldn't load your plan — please try again in a moment");
    }
  };

  useEffect(() => { loadStatus().then((s) => { if (s.active) loadPlusData(); }); }, []);

  const startTrial = async () => {
    setBusy(true);
    try {
      await api.post("/plus/start-trial");
      await refresh();
      const s = await loadStatus();
      if (s.active) await loadPlusData();
      toast.success("Your 14-day trial is on. Let's build your first plan.");
    } catch (e) { toast.error(e?.response?.data?.detail || "Could not start trial"); }
    finally { setBusy(false); }
  };
  const checkout = async (package_id, extra = {}) => {
    setBusy(true);
    try {
      const { data } = await api.post("/payments/checkout", { package_id, origin_url: window.location.origin, ...extra });
      window.location.href = data.checkout_url;
    } catch (e) { toast.error(e?.response?.data?.detail || "Could not start checkout"); setBusy(false); }
  };
  const toggleItem = async (idx) => {
    const { data } = await api.put("/wellness/plan/toggle", { item_index: idx });
    setPlan((p) => ({ ...p, items: data.items }));
  };
  const regenerate = async () => {
    setBusy(true);
    try { const { data } = await api.post("/wellness/plan/regenerate"); setPlan(data); toast.success("Fresh plan for today"); }
    finally { setBusy(false); }
  };
  const logFood = async () => {
    if (!foodText.trim()) return;
    setBusy(true);
    try { await api.post("/wellness/food", { text: foodText }); setFoodText(""); const { data } = await api.get("/wellness/food"); setFood(data); }
    finally { setBusy(false); }
  };
  const delFood = async (id) => { await api.delete(`/wellness/food/${id}`); const { data } = await api.get("/wellness/food"); setFood(data); };
  const addEvent = async () => {
    if (!evtTitle.trim()) return;
    const today = new Date().toISOString().slice(0, 10);
    const { data } = await api.post("/wellness/events", { title: evtTitle, start: `${today}T${evtTime}`, type: "task" });
    setEvents((e) => [...e, data].sort((a, b) => a.start.localeCompare(b.start))); setEvtTitle("");
  };
  const delEvent = async (id) => { await api.delete(`/wellness/events/${id}`); setEvents((e) => e.filter((x) => x.id !== id)); };

  if (loading) return <div className="min-h-screen bg-background flex items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;

  const Header = () => (
    <header className="glass sticky top-0 z-30 h-16 flex items-center justify-between px-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" className="rounded-full" onClick={() => navigate("/chat")} data-testid="wellness-back-button"><ArrowLeft className="h-4 w-4" /></Button>
        <span className="font-display font-semibold text-xl tracking-tight">CampionAI <span className="italic font-light">Plus</span></span>
      </div>
      {status.active && (
        <span className="text-[10px] tracking-[0.2em] uppercase border border-border px-2 py-1 rounded-full text-foreground/60" data-testid="plus-status-badge">
          {status.status === "trialing" ? "Trial" : "Active"}
        </span>
      )}
    </header>
  );

  if (!status.active) {
    const onActivated = async () => { await refresh(); const s = await loadStatus(); if (s.active) await loadPlusData(); };
    return <div className="min-h-screen bg-background relative"><Glow /><Header /><Paywall status={status} onTrial={startTrial} onCheckout={checkout} onDonate={checkout} onActivated={onActivated} busy={busy} /></div>;
  }

  const items = plan?.items || [];
  const doneCount = items.filter((i) => i.done).length;
  const donePct = items.length ? Math.round((doneCount / items.length) * 100) : 0;
  const t = food.totals || {};

  return (
    <div className="min-h-screen bg-background relative">
      <Glow />
      <Header />
      <div className="relative z-10 max-w-3xl mx-auto px-6 py-10">
        {/* Hero */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="mb-10">
          <p className="text-[10px] tracking-[0.3em] uppercase text-muted-foreground mb-3">
            {new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}
          </p>
          <h1 className="font-display font-light text-4xl md:text-5xl tracking-tight mb-6">Good to see you, {name}.</h1>
          <div className="flex items-center gap-4">
            <div className="flex-1 h-1.5 rounded-full bg-border overflow-hidden">
              <motion.div className="h-full bg-foreground rounded-full" initial={{ width: 0 }} animate={{ width: `${donePct}%` }} transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }} />
            </div>
            <span className="text-sm text-muted-foreground font-mono-data shrink-0">{doneCount}/{items.length} done</span>
          </div>
        </motion.div>

        <Tabs defaultValue="plan">
          <TabsList className="rounded-full">
            <TabsTrigger value="plan" className="rounded-full" data-testid="wellness-tab-plan">Today's plan</TabsTrigger>
            <TabsTrigger value="food" className="rounded-full" data-testid="wellness-tab-food">Food</TabsTrigger>
            <TabsTrigger value="schedule" className="rounded-full" data-testid="wellness-tab-schedule">Schedule</TabsTrigger>
          </TabsList>

          {/* PLAN */}
          <TabsContent value="plan" className="mt-8">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-display font-light text-2xl">Your day, gently planned.</h2>
              <Button variant="outline" size="sm" className="rounded-full border-border gap-1.5" onClick={regenerate} disabled={busy} data-testid="regenerate-plan-button">
                <RefreshCw className={`h-3.5 w-3.5 ${busy ? "animate-spin" : ""}`} /> New plan
              </Button>
            </div>
            <div className="space-y-3">
              {items.map((it, idx) => {
                const Icon = TYPE_ICON[it.type] || Sparkles;
                return (
                  <motion.div key={idx} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: idx * 0.05 }}
                    className={`group flex items-center gap-4 p-5 rounded-2xl border transition-colors ${it.done ? "border-border bg-card/30" : "border-border bg-card/50 hover:border-foreground/30"}`} data-testid={`plan-item-${idx}`}>
                    <div className={`h-11 w-11 rounded-xl flex items-center justify-center shrink-0 border ${it.done ? "border-border bg-transparent" : "border-border bg-white/[0.04]"}`}>
                      <Icon className={`h-5 w-5 ${it.done ? "text-muted-foreground" : "text-foreground/80"}`} strokeWidth={1.5} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className={`font-medium ${it.done ? "line-through text-muted-foreground" : ""}`}>{it.title}</p>
                        <span className="text-[10px] tracking-[0.12em] uppercase text-muted-foreground/70 border border-border rounded-full px-2 py-0.5">{it.type}</span>
                      </div>
                      <p className="text-sm text-muted-foreground mt-0.5">{it.detail}</p>
                      <p className="text-[11px] text-muted-foreground/70 font-mono-data mt-1.5">{it.duration_min} min · {it.time_of_day}</p>
                    </div>
                    <button onClick={() => toggleItem(idx)} data-testid={`toggle-item-${idx}`}
                      className={`h-8 w-8 rounded-full border flex items-center justify-center shrink-0 transition-all ${it.done ? "bg-primary border-primary scale-100" : "border-border hover:border-foreground hover:scale-105"}`}>
                      {it.done && <Check className="h-4 w-4 text-primary-foreground" strokeWidth={2.5} />}
                    </button>
                  </motion.div>
                );
              })}
            </div>
          </TabsContent>

          {/* FOOD */}
          <TabsContent value="food" className="mt-8">
            <div className="rounded-2xl border border-border bg-card/50 p-6 mb-6" data-testid="food-totals">
              <div className="flex flex-col sm:flex-row items-center gap-8">
                <CalorieRing value={t.calories || 0} />
                <div className="flex-1 w-full space-y-4">
                  <MacroBar label="Protein" value={t.protein_g || 0} target={MACRO_TARGETS.protein_g} />
                  <MacroBar label="Carbs" value={t.carbs_g || 0} target={MACRO_TARGETS.carbs_g} />
                  <MacroBar label="Fat" value={t.fat_g || 0} target={MACRO_TARGETS.fat_g} />
                </div>
              </div>
            </div>

            <div className="flex gap-2 mb-6">
              <Input className="rounded-full h-11" placeholder='Describe a meal — "2 rotis and dal"…' value={foodText}
                onChange={(e) => setFoodText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && logFood()} data-testid="food-input" />
              <Button className="rounded-full bg-primary text-primary-foreground hover:bg-zinc-200 px-6" onClick={logFood} disabled={busy} data-testid="log-food-button">
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Log"}
              </Button>
            </div>

            <div className="space-y-2">
              {food.logs?.length === 0 && <p className="text-sm text-muted-foreground rounded-2xl border border-border bg-card/30 p-5">Nothing logged yet today.</p>}
              {food.logs?.map((l) => (
                <div key={l.id} className="group flex items-center justify-between rounded-2xl border border-border bg-card/50 p-4" data-testid={`food-log-${l.id}`}>
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="h-9 w-9 rounded-lg bg-white/[0.04] border border-border flex items-center justify-center shrink-0"><Utensils className="h-4 w-4 text-foreground/70" strokeWidth={1.5} /></div>
                    <div className="min-w-0"><p className="text-sm font-medium truncate">{l.summary}</p><p className="text-[11px] text-muted-foreground font-mono-data">{l.calories} kcal · P{l.protein_g} C{l.carbs_g} F{l.fat_g}</p></div>
                  </div>
                  <button onClick={() => delFood(l.id)} className="text-muted-foreground hover:text-escalation opacity-0 group-hover:opacity-100 transition-opacity shrink-0"><Trash2 className="h-4 w-4" /></button>
                </div>
              ))}
            </div>
          </TabsContent>

          {/* SCHEDULE */}
          <TabsContent value="schedule" className="mt-8">
            <h2 className="font-display font-light text-2xl mb-2 flex items-center gap-2"><CalendarClock className="h-5 w-5 text-muted-foreground" /> Today's schedule</h2>
            <p className="text-muted-foreground mb-6">Give your intentions a time. Small commitments, kept.</p>
            <div className="flex flex-col sm:flex-row gap-2 mb-8">
              <Input type="time" className="rounded-full h-11 w-full sm:w-32" value={evtTime} onChange={(e) => setEvtTime(e.target.value)} data-testid="event-time-input" />
              <div className="flex gap-2 flex-1">
                <Input className="rounded-full h-11 flex-1" placeholder="Add something to your day…" value={evtTitle}
                  onChange={(e) => setEvtTitle(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addEvent()} data-testid="event-title-input" />
                <Button size="icon" className="rounded-full bg-primary text-primary-foreground hover:bg-zinc-200 shrink-0" onClick={addEvent} data-testid="add-event-button"><Plus className="h-4 w-4" /></Button>
              </div>
            </div>

            {events.length === 0 ? (
              <p className="text-sm text-muted-foreground rounded-2xl border border-border bg-card/30 p-5">Your day is open. Add a moment above.</p>
            ) : (
              <div className="relative pl-6">
                <div className="absolute left-[7px] top-2 bottom-2 w-px bg-border" />
                <div className="space-y-4">
                  {events.map((ev) => (
                    <motion.div key={ev.id} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4 }}
                      className="relative group flex items-center gap-4" data-testid={`event-${ev.id}`}>
                      <span className="absolute -left-6 top-1/2 -translate-y-1/2 h-3 w-3 rounded-full bg-foreground/70 ring-4 ring-background" />
                      <span className="font-mono-data text-sm text-muted-foreground w-14 shrink-0">{ev.start.slice(11, 16)}</span>
                      <div className="flex-1 rounded-2xl border border-border bg-card/50 p-4 flex items-center justify-between">
                        <p className="text-sm font-medium">{ev.title}</p>
                        <button onClick={() => delEvent(ev.id)} className="text-muted-foreground hover:text-escalation opacity-0 group-hover:opacity-100 transition-opacity"><Trash2 className="h-4 w-4" /></button>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
