import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { toast } from "@/components/ui/sonner";
import {
  ArrowLeft, Sparkles, Check, RefreshCw, Utensils, CalendarClock, Plus, Trash2,
  Wind, Flower2, Activity, Brain, HeartHandshake, Loader2, Heart,
} from "lucide-react";

const TYPE_ICON = { breathing: Wind, yoga: Flower2, movement: Activity, meditation: Brain, task: HeartHandshake };

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

function Paywall({ status, onTrial, onCheckout, onDonate, busy }) {
  const plans = [
    { id: "plus_monthly", price: "$9", per: "/mo", note: "Billed monthly" },
    { id: "plus_yearly", price: "$86.40", per: "/yr", note: "Just $7.20/mo · billed yearly", featured: true, save: "Save 20%" },
  ];
  return (
    <div className="max-w-3xl mx-auto px-6 py-16 md:py-20">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}>
        <p className="text-[10px] tracking-[0.3em] uppercase text-muted-foreground mb-5 flex items-center gap-2"><Sparkles className="h-3.5 w-3.5" /> CampionAI Plus</p>
        <h1 className="font-display font-light text-4xl md:text-6xl tracking-tight leading-[1.02] mb-5">
          Your companion becomes<br /><span className="italic">your daily coach.</span>
        </h1>
        <p className="text-muted-foreground text-lg leading-relaxed mb-12 max-w-xl">
          A gentle, personal wellness rhythm — and CampionAI weaves it into your conversations, so it feels
          less like an app and more like a friend cheering you on.
        </p>

        {/* What's included */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-px bg-border border border-border mb-14">
          {INCLUDED.map((f) => (
            <div key={f.label} className="bg-background p-6 flex items-start gap-4">
              <f.icon className="h-5 w-5 text-foreground/80 mt-0.5 shrink-0" strokeWidth={1.5} />
              <div>
                <p className="font-medium">{f.label}</p>
                <p className="text-sm text-muted-foreground leading-relaxed">{f.note}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Pricing */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 mb-6">
          {plans.map((p) => (
            <div key={p.id}
              className={`relative p-8 transition-colors ${p.featured ? "border border-foreground bg-white/[0.03]" : "border border-border hover:border-foreground/40"}`}
              data-testid={`plan-${p.id}`}>
              {p.save && (
                <span className="absolute -top-3 left-8 bg-primary text-primary-foreground text-[10px] tracking-[0.15em] uppercase px-3 py-1">{p.save}</span>
              )}
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
              <Button
                className={`w-full rounded-full ${p.featured ? "bg-primary text-primary-foreground hover:bg-zinc-200" : "bg-transparent border border-border text-foreground hover:bg-accent"}`}
                onClick={() => onCheckout(p.id)} disabled={busy} data-testid={`subscribe-${p.id}`}>
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : `Choose ${p.featured ? "yearly" : "monthly"}`}
              </Button>
            </div>
          ))}
        </div>
        <p className="text-center text-xs text-muted-foreground mb-14">Every plan starts with a 14-day free trial. No charge today.</p>

        {/* Trial */}
        {!status.trial_used && (
          <div className="border border-border bg-white/[0.02] p-7 flex flex-col sm:flex-row sm:items-center justify-between gap-5 mb-16">
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

        {/* Donation */}
        <div className="border-t border-border pt-12">
          <p className="text-[10px] tracking-[0.3em] uppercase text-muted-foreground mb-3 flex items-center gap-2"><Heart className="h-3.5 w-3.5" /> Keep CampionAI free for everyone</p>
          <p className="text-muted-foreground mb-6 max-w-lg leading-relaxed">
            CampionAI is free for individuals — and always will be. If Plus isn't for you but you'd like to help,
            a small donation keeps the lights on for people who need it.
          </p>
          <div className="flex flex-wrap gap-3">
            {[["donate_5", "$5"], ["donate_15", "$15"], ["donate_30", "$30"]].map(([id, label]) => (
              <Button key={id} variant="outline" className="rounded-full border-border hover:border-foreground/40 hover:bg-accent px-6" onClick={() => onDonate(id)} disabled={busy} data-testid={`donate-${id}`}>
                <Heart className="h-3.5 w-3.5 mr-2 text-foreground/60" strokeWidth={1.5} /> Donate {label}
              </Button>
            ))}
          </div>
        </div>
      </motion.div>
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

  const loadStatus = async () => {
    const { data } = await api.get("/plus/status");
    setStatus(data);
    setLoading(false);
    return data;
  };

  const loadPlusData = async () => {
    const today = new Date().toISOString().slice(0, 10);
    try {
      const [p, f, e] = await Promise.all([
        api.get("/wellness/plan"), api.get("/wellness/food"), api.get(`/wellness/events?date=${today}`),
      ]);
      setPlan(p.data); setFood(f.data); setEvents(e.data);
    } catch (err) {
      toast.error("Couldn't load your plan — please try again in a moment");
    }
  };

  useEffect(() => {
    loadStatus().then((s) => { if (s.active) loadPlusData(); });
  }, []);

  const startTrial = async () => {
    setBusy(true);
    try {
      await api.post("/plus/start-trial");
      await refresh();
      const s = await loadStatus();
      if (s.active) await loadPlusData();
      toast.success("Your 14-day trial is on. Let's build your first plan.");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not start trial");
    } finally { setBusy(false); }
  };

  const checkout = async (package_id) => {
    setBusy(true);
    try {
      const { data } = await api.post("/payments/checkout", { package_id, origin_url: window.location.origin });
      window.location.href = data.checkout_url;
    } catch (e) {
      toast.error("Could not start checkout");
      setBusy(false);
    }
  };

  const toggleItem = async (idx) => {
    const { data } = await api.put("/wellness/plan/toggle", { item_index: idx });
    setPlan((p) => ({ ...p, items: data.items }));
  };

  const regenerate = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/wellness/plan/regenerate");
      setPlan(data);
      toast.success("Fresh plan for today");
    } finally { setBusy(false); }
  };

  const logFood = async () => {
    if (!foodText.trim()) return;
    setBusy(true);
    try {
      await api.post("/wellness/food", { text: foodText });
      setFoodText("");
      const { data } = await api.get("/wellness/food");
      setFood(data);
    } finally { setBusy(false); }
  };

  const delFood = async (id) => {
    await api.delete(`/wellness/food/${id}`);
    const { data } = await api.get("/wellness/food");
    setFood(data);
  };

  const addEvent = async () => {
    if (!evtTitle.trim()) return;
    const today = new Date().toISOString().slice(0, 10);
    const { data } = await api.post("/wellness/events", { title: evtTitle, start: `${today}T${evtTime}`, type: "task" });
    setEvents((e) => [...e, data].sort((a, b) => a.start.localeCompare(b.start)));
    setEvtTitle("");
  };

  const delEvent = async (id) => {
    await api.delete(`/wellness/events/${id}`);
    setEvents((e) => e.filter((x) => x.id !== id));
  };

  if (loading) {
    return <div className="min-h-screen bg-background flex items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  }

  const Header = () => (
    <header className="glass sticky top-0 z-20 h-16 flex items-center justify-between px-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" className="rounded-full" onClick={() => navigate("/chat")} data-testid="wellness-back-button">
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <span className="font-display font-semibold text-xl tracking-tight">CampionAI <span className="italic font-light">Plus</span></span>
      </div>
      {status.active && (
        <span className="text-[10px] tracking-[0.2em] uppercase border border-border px-2 py-1 text-foreground/60" data-testid="plus-status-badge">
          {status.status === "trialing" ? "Trial" : "Active"}
        </span>
      )}
    </header>
  );

  if (!status.active) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <Paywall status={status} onTrial={startTrial} onCheckout={checkout} onDonate={checkout} busy={busy} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="max-w-3xl mx-auto px-6 py-10">
        <Tabs defaultValue="plan">
          <TabsList className="rounded-full">
            <TabsTrigger value="plan" className="rounded-full" data-testid="wellness-tab-plan">Today's plan</TabsTrigger>
            <TabsTrigger value="food" className="rounded-full" data-testid="wellness-tab-food">Food</TabsTrigger>
            <TabsTrigger value="schedule" className="rounded-full" data-testid="wellness-tab-schedule">Schedule</TabsTrigger>
          </TabsList>

          {/* PLAN */}
          <TabsContent value="plan" className="mt-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-display font-light text-3xl">Your day, gently planned.</h2>
              <Button variant="outline" size="sm" className="rounded-full border-border gap-1.5" onClick={regenerate} disabled={busy} data-testid="regenerate-plan-button">
                <RefreshCw className={`h-3.5 w-3.5 ${busy ? "animate-spin" : ""}`} /> New plan
              </Button>
            </div>
            <div className="space-y-px bg-border border border-border">
              {plan?.items?.map((it, idx) => {
                const Icon = TYPE_ICON[it.type] || Sparkles;
                return (
                  <div key={idx} className="bg-background flex items-center gap-4 p-5" data-testid={`plan-item-${idx}`}>
                    <button onClick={() => toggleItem(idx)} data-testid={`toggle-item-${idx}`}
                      className={`h-7 w-7 rounded-full border flex items-center justify-center shrink-0 transition-colors ${it.done ? "bg-primary border-primary" : "border-border hover:border-foreground"}`}>
                      {it.done && <Check className="h-4 w-4 text-primary-foreground" />}
                    </button>
                    <Icon className="h-4 w-4 text-muted-foreground shrink-0" strokeWidth={1.5} />
                    <div className="flex-1 min-w-0">
                      <p className={`font-medium ${it.done ? "line-through text-muted-foreground" : ""}`}>{it.title}</p>
                      <p className="text-sm text-muted-foreground">{it.detail}</p>
                    </div>
                    <span className="text-[11px] text-muted-foreground font-mono-data shrink-0">{it.duration_min}m · {it.time_of_day}</span>
                  </div>
                );
              })}
            </div>
          </TabsContent>

          {/* FOOD */}
          <TabsContent value="food" className="mt-8">
            <h2 className="font-display font-light text-3xl mb-2">What did you eat?</h2>
            <p className="text-muted-foreground mb-6">Just describe it — "2 rotis and dal" — and I'll estimate the rest.</p>
            <div className="flex gap-2 mb-6">
              <Input className="rounded-full h-11" placeholder="Describe a meal…" value={foodText}
                onChange={(e) => setFoodText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && logFood()} data-testid="food-input" />
              <Button className="rounded-full bg-primary text-primary-foreground hover:bg-zinc-200" onClick={logFood} disabled={busy} data-testid="log-food-button">
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Log"}
              </Button>
            </div>

            <div className="grid grid-cols-4 gap-px bg-border border border-border mb-6" data-testid="food-totals">
              {[["calories", "kcal"], ["protein_g", "protein"], ["carbs_g", "carbs"], ["fat_g", "fat"]].map(([k, l]) => (
                <div key={k} className="bg-background p-4 text-center">
                  <p className="font-display font-light text-2xl">{food.totals?.[k] || 0}</p>
                  <p className="text-[10px] tracking-[0.15em] uppercase text-muted-foreground">{l}</p>
                </div>
              ))}
            </div>

            <div className="space-y-px bg-border border border-border">
              {food.logs?.length === 0 && <p className="bg-background p-5 text-sm text-muted-foreground">Nothing logged yet today.</p>}
              {food.logs?.map((l) => (
                <div key={l.id} className="bg-background flex items-center justify-between p-4" data-testid={`food-log-${l.id}`}>
                  <div><p className="text-sm font-medium">{l.summary}</p><p className="text-[11px] text-muted-foreground font-mono-data">{l.calories} kcal · P{l.protein_g} C{l.carbs_g} F{l.fat_g}</p></div>
                  <button onClick={() => delFood(l.id)} className="text-muted-foreground hover:text-escalation"><Trash2 className="h-4 w-4" /></button>
                </div>
              ))}
            </div>
          </TabsContent>

          {/* SCHEDULE */}
          <TabsContent value="schedule" className="mt-8">
            <h2 className="font-display font-light text-3xl mb-2 flex items-center gap-2"><CalendarClock className="h-6 w-6 text-muted-foreground" /> Today's schedule</h2>
            <p className="text-muted-foreground mb-6">Give your intentions a time. Small commitments, kept.</p>
            <div className="flex flex-col sm:flex-row gap-2 mb-6">
              <Input type="time" className="rounded-full h-11 w-full sm:w-32" value={evtTime} onChange={(e) => setEvtTime(e.target.value)} data-testid="event-time-input" />
              <div className="flex gap-2 flex-1">
                <Input className="rounded-full h-11 flex-1" placeholder="Add something to your day…" value={evtTitle}
                  onChange={(e) => setEvtTitle(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addEvent()} data-testid="event-title-input" />
                <Button size="icon" className="rounded-full bg-primary text-primary-foreground hover:bg-zinc-200 shrink-0" onClick={addEvent} data-testid="add-event-button"><Plus className="h-4 w-4" /></Button>
              </div>
            </div>
            <div className="space-y-px bg-border border border-border">
              {events.length === 0 && <p className="bg-background p-5 text-sm text-muted-foreground">Your day is open. Add a moment above.</p>}
              {events.map((ev) => (
                <div key={ev.id} className="bg-background flex items-center gap-4 p-4" data-testid={`event-${ev.id}`}>
                  <span className="font-mono-data text-sm text-muted-foreground w-14 shrink-0">{ev.start.slice(11, 16)}</span>
                  <p className="flex-1 text-sm font-medium">{ev.title}</p>
                  <button onClick={() => delEvent(ev.id)} className="text-muted-foreground hover:text-escalation"><Trash2 className="h-4 w-4" /></button>
                </div>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
