import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useVisibilityRefetch } from "@/hooks/use-visibility-refetch";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "@/components/ui/sonner";
import PayPalSubscribe, { PayPalDonate } from "@/components/PayPalSubscribe";
import AccountMenu from "@/components/AccountMenu";
import {
  ArrowLeft, Sparkles, Check, RefreshCw, Utensils, CalendarClock, Plus, Trash2,
  Wind, Flower2, Activity, Brain, HeartHandshake, Loader2, Heart,
  Flame, ChevronUp, ChevronDown, PartyPopper,
  Smile, Meh, Frown, Sprout, Medal, Trophy, Quote,
} from "lucide-react";
import BreathingPlayer from "@/components/BreathingPlayer";

const MEALS = ["breakfast", "lunch", "dinner", "snack"];
const BADGE_ICON = { sprout: Sprout, flame: Flame, medal: Medal, trophy: Trophy, heart: Heart, smile: Smile };
const MOODS = [
  { v: 1, label: "Rough", Icon: Frown },
  { v: 2, label: "Low", Icon: Frown },
  { v: 3, label: "Okay", Icon: Meh },
  { v: 4, label: "Good", Icon: Smile },
  { v: 5, label: "Great", Icon: Smile },
];

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

function Paywall({ status, onTrial, onActivated, busy }) {
  const [pricing, setPricing] = useState(null);
  const [donors, setDonors] = useState([]);
  const [custom, setCustom] = useState("");
  const [anon, setAnon] = useState(false);
  const [donateAmount, setDonateAmount] = useState(null);

  const loadDonors = () => api.get("/donors/top").then(({ data }) => setDonors(data)).catch(() => {});
  useEffect(() => {
    api.get("/pricing").then(({ data }) => setPricing(data)).catch(() => toast.error("Couldn't load pricing"));
    loadDonors();
  }, []);

  const pickCustom = () => {
    const amt = parseFloat(custom);
    if (!amt || amt < 1) { toast.error("Enter an amount of at least $1"); return; }
    setDonateAmount(amt);
  };

  const afterDonation = () => { setDonateAmount(null); setCustom(""); loadDonors(); };

  if (!pricing) {
    return <div className="relative z-10 flex justify-center py-32"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  }

  const clientId = pricing.paypal_client_id;
  const plansReady = clientId && pricing.plans.some((p) => p.paypal_plan_id);

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
          {pricing.plans.map((p) => (
            <div key={p.id}
              className={`relative p-8 rounded-2xl transition-colors ${p.featured ? "border border-foreground bg-white/[0.04] ambient-shadow-lg" : "border border-border bg-card/40 hover:border-foreground/40"}`}
              data-testid={`plan-${p.id}`}>
              {p.save && <span className="absolute -top-3 left-8 bg-primary text-primary-foreground text-[10px] tracking-[0.15em] uppercase px-3 py-1 rounded-full">{p.save}</span>}
              <div className="flex items-end gap-1.5 mb-1">
                <span className="font-display font-light text-5xl leading-none">${p.amount}</span>
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
              {p.paypal_plan_id ? (
                <PayPalSubscribe
                  clientId={clientId}
                  planId={p.paypal_plan_id}
                  planKey={p.id === "plus_yearly" ? "yearly" : "monthly"}
                  onActivated={onActivated}
                />
              ) : (
                <p className="text-xs text-muted-foreground" data-testid={`plan-unavailable-${p.id}`}>
                  Card payments aren't set up yet — check back soon.
                </p>
              )}
            </div>
          ))}
        </div>
        {plansReady && (
          <p className="text-center text-xs text-muted-foreground mb-14">
            Subscriptions renew automatically. Cancel anytime from Billing.
          </p>
        )}

        {!status.trial_used && (
          <div className="border border-border bg-card/40 rounded-2xl p-7 flex flex-col sm:flex-row sm:items-center justify-between gap-5 mb-16">
            <div className="flex items-start gap-4">
              <Sparkles className="h-5 w-5 text-foreground/70 mt-0.5 shrink-0" strokeWidth={1.5} />
              <div>
                <p className="font-medium">Not ready to commit?</p>
                <p className="text-sm text-muted-foreground">Try everything free for {pricing.trial_days} days. No card needed.</p>
              </div>
            </div>
            <Button className="rounded-full bg-primary text-primary-foreground hover:bg-zinc-200 shrink-0 px-7" onClick={onTrial} disabled={busy} data-testid="start-trial-button">
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : `Start ${pricing.trial_days}-day free trial`}
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
            {pricing.donations.map((d) => (
              <Button key={d.id} variant="outline"
                className={`rounded-full px-5 ${donateAmount === d.amount ? "border-foreground bg-accent" : "border-border hover:border-foreground/40 hover:bg-accent"}`}
                onClick={() => { setCustom(""); setDonateAmount(d.amount); }} data-testid={`donate-${d.id}`}>
                ${d.amount}
              </Button>
            ))}
          </div>

          <div className="flex gap-2 max-w-sm mb-3">
            <div className="relative flex-1">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
              <Input type="number" min="1" step="1" className="rounded-full h-11 pl-7" placeholder="Custom amount" value={custom}
                onChange={(e) => setCustom(e.target.value)} onKeyDown={(e) => e.key === "Enter" && pickCustom()} data-testid="custom-donate-input" />
            </div>
            <Button className="rounded-full bg-primary text-primary-foreground hover:bg-zinc-200 px-6" onClick={pickCustom} data-testid="custom-donate-button">
              Use amount
            </Button>
          </div>
          <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer mb-5">
            <Checkbox checked={anon} onCheckedChange={(v) => setAnon(!!v)} data-testid="donate-anonymous-checkbox" />
            Donate anonymously (won't appear on the supporters list)
          </label>

          {donateAmount ? (
            <div className="max-w-sm mb-12" data-testid="donate-paypal-wrap">
              <p className="text-sm text-muted-foreground mb-3">Donating <span className="text-foreground font-medium">${donateAmount.toFixed(2)}</span></p>
              {clientId
                ? <PayPalDonate clientId={clientId} amount={donateAmount} anonymous={anon} onDone={afterDonation} />
                : <p className="text-xs text-muted-foreground">Donations aren't set up yet.</p>}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground mb-12">Pick an amount above to continue.</p>
          )}

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
  const [streak, setStreak] = useState({ current: 0, best: 0 });
  const [newTodo, setNewTodo] = useState("");
  const [meal, setMeal] = useState("breakfast");
  const [trends, setTrends] = useState({ series: [], average: null, today: null });
  const [moodNote, setMoodNote] = useState("");
  const [gratitude, setGratitude] = useState({ items: [] });
  const [gratInput, setGratInput] = useState("");
  const [badges, setBadges] = useState({ badges: [], earned_count: 0 });

  const name = user?.profile?.preferred_name || "friend";

  const loadStatus = async () => {
    const { data } = await api.get("/plus/status");
    setStatus(data); setLoading(false); return data;
  };
  const loadStreak = async () => {
    try { const { data } = await api.get("/wellness/streak"); setStreak(data); } catch { /* best-effort */ }
  };
  const loadExtras = async () => {
    try {
      const [t, g, b] = await Promise.all([
        api.get("/wellness/mood/trends?days=30"), api.get("/wellness/gratitude"), api.get("/wellness/badges"),
      ]);
      setTrends(t.data); setGratitude(g.data); setBadges(b.data);
    } catch { /* best-effort */ }
  };
  const loadPlusData = async () => {
    const today = new Date().toISOString().slice(0, 10);
    try {
      const [p, f, e] = await Promise.all([
        api.get("/wellness/plan"), api.get("/wellness/food"), api.get(`/wellness/events?date=${today}`),
      ]);
      setPlan(p.data); setFood(f.data); setEvents(e.data);
      loadStreak();
      loadExtras();
    } catch {
      toast.error("Couldn't load your plan — please try again in a moment");
    }
  };

  const logMood = async (mood) => {
    try {
      await api.post("/wellness/mood", { mood, note: moodNote });
      setMoodNote("");
      toast.success("Mood logged — thanks for checking in");
      loadExtras();
    } catch { toast.error("Couldn't log that"); }
  };
  const addGratitude = async () => {
    if (!gratInput.trim()) return;
    try {
      await api.post("/wellness/gratitude", { text: gratInput.trim() });
      setGratInput("");
      loadExtras();
    } catch { toast.error("Couldn't add that"); }
  };
  const delGratitude = async (gid) => {
    try { await api.delete(`/wellness/gratitude/${gid}`); loadExtras(); } catch { /* noop */ }
  };

  useEffect(() => { loadStatus().then((s) => { if (s.active) loadPlusData(); }); }, []);

  // Refresh Plus/subscription status (and plan data) when returning to the tab —
  // e.g. right after completing a PayPal/Stripe checkout in another tab.
  useVisibilityRefetch(async () => {
    try {
      await refresh();
      const s = await loadStatus();
      if (s.active) await loadPlusData();
    } catch { /* best-effort */ }
  });

  const startTrial = async () => {
    setBusy(true);
    try {
      await api.post("/plus/start-trial");
      await refresh();
      const s = await loadStatus();
      if (s.active) await loadPlusData();
      toast.success("Your free trial is on. Let's build your first plan.");
    } catch (e) { toast.error(e?.response?.data?.detail || "Could not start trial"); }
    finally { setBusy(false); }
  };
  const toggleItem = async (idx) => {
    const { data } = await api.put("/wellness/plan/toggle", { item_index: idx });
    setPlan((p) => ({ ...p, items: data.items }));
    loadStreak();
  };
  const addTodo = async () => {
    if (!newTodo.trim()) return;
    try {
      const { data } = await api.post("/wellness/plan/item", { title: newTodo.trim() });
      setPlan((p) => ({ ...p, items: data.items }));
      setNewTodo("");
      toast.success("Added to your plan");
    } catch { toast.error("Couldn't add that"); }
  };
  const delItem = async (idx) => {
    try {
      const { data } = await api.delete(`/wellness/plan/item/${idx}`);
      setPlan((p) => ({ ...p, items: data.items }));
    } catch { toast.error("Couldn't remove that"); }
  };
  const moveItem = async (idx, dir) => {
    const items = plan?.items || [];
    const j = idx + dir;
    if (j < 0 || j >= items.length) return;
    const order = items.map((_, i) => i);
    [order[idx], order[j]] = [order[j], order[idx]];
    // optimistic
    const reordered = order.map((i) => items[i]);
    setPlan((p) => ({ ...p, items: reordered }));
    try {
      const { data } = await api.put("/wellness/plan/reorder", { order });
      setPlan((p) => ({ ...p, items: data.items }));
    } catch { setPlan((p) => ({ ...p, items })); }
  };
  const regenerate = async () => {
    setBusy(true);
    try { const { data } = await api.post("/wellness/plan/regenerate"); setPlan(data); toast.success("Fresh plan for today"); }
    finally { setBusy(false); }
  };
  const logFood = async () => {
    if (!foodText.trim()) return;
    setBusy(true);
    try { await api.post("/wellness/food", { text: foodText, meal }); setFoodText(""); const { data } = await api.get("/wellness/food"); setFood(data); }
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
      <div className="flex items-center gap-3">
        {streak.current > 0 && (
          <span className="flex items-center gap-1.5 text-[11px] tracking-[0.1em] uppercase border border-amber-400/40 text-amber-400/90 px-2.5 py-1 rounded-full" data-testid="streak-badge" title={`Best streak: ${streak.best} days`}>
            <Flame className="h-3.5 w-3.5" /> {streak.current}-day streak
          </span>
        )}
        {status.active && (
          <span className="text-[10px] tracking-[0.2em] uppercase border border-border px-2 py-1 rounded-full text-foreground/60" data-testid="plus-status-badge">
            {status.status === "trialing" ? "Trial" : "Active"}
          </span>
        )}
        <AccountMenu />
      </div>
    </header>
  );

  if (!status.active) {
    const onActivated = async () => { await refresh(); const s = await loadStatus(); if (s.active) await loadPlusData(); };
    return <div className="min-h-screen bg-background relative"><Glow /><Header /><Paywall status={status} onTrial={startTrial} onActivated={onActivated} busy={busy} /></div>;
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

        {/* Badges strip */}
        {badges.badges.length > 0 && (
          <div className="flex items-center gap-2 mb-8 overflow-x-auto pb-1" data-testid="badges-strip">
            {badges.badges.map((b) => {
              const Icon = BADGE_ICON[b.icon] || Sparkles;
              return (
                <div key={b.id} title={b.earned ? `Earned: ${b.label}` : `${b.value}/${b.threshold} · ${b.label}`}
                  className={`shrink-0 flex items-center gap-2 rounded-full border px-3 py-1.5 transition-colors ${b.earned ? "border-amber-400/40 bg-amber-400/[0.06] text-amber-300/90" : "border-border text-muted-foreground/60"}`}
                  data-testid={`badge-${b.id}`}>
                  <Icon className="h-3.5 w-3.5" strokeWidth={1.5} />
                  <span className="text-[11px] tracking-[0.04em] whitespace-nowrap">{b.label}</span>
                  {!b.earned && <span className="text-[10px] font-mono-data opacity-70">{b.value}/{b.threshold}</span>}
                </div>
              );
            })}
          </div>
        )}

        <Tabs defaultValue="plan">
          <TabsList className="rounded-full flex-wrap h-auto">
            <TabsTrigger value="plan" className="rounded-full" data-testid="wellness-tab-plan">Today's plan</TabsTrigger>
            <TabsTrigger value="mood" className="rounded-full" data-testid="wellness-tab-mood">Mood</TabsTrigger>
            <TabsTrigger value="breathe" className="rounded-full" data-testid="wellness-tab-breathe">Breathe</TabsTrigger>
            <TabsTrigger value="gratitude" className="rounded-full" data-testid="wellness-tab-gratitude">Gratitude</TabsTrigger>
            <TabsTrigger value="food" className="rounded-full" data-testid="wellness-tab-food">Food</TabsTrigger>
            <TabsTrigger value="schedule" className="rounded-full" data-testid="wellness-tab-schedule">Schedule</TabsTrigger>
          </TabsList>

          {/* PLAN */}
          <TabsContent value="plan" className="mt-8">
            {items.length > 0 && donePct === 100 && (
              <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }}
                className="mb-5 rounded-2xl border border-amber-400/40 bg-amber-400/[0.06] p-5 flex items-center gap-4" data-testid="plan-complete-celebration">
                <PartyPopper className="h-6 w-6 text-amber-400 shrink-0" strokeWidth={1.5} />
                <div>
                  <p className="font-medium">That's your whole day, done.</p>
                  <p className="text-sm text-muted-foreground">
                    Beautiful work, {name}. {streak.current > 1 ? `That's ${streak.current} days in a row.` : "Come back tomorrow to start a streak."}
                  </p>
                </div>
              </motion.div>
            )}
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
                  <motion.div key={idx} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: idx * 0.03 }}
                    className={`group flex items-center gap-3 p-5 rounded-2xl border transition-colors ${it.done ? "border-border bg-card/30" : "border-border bg-card/50 hover:border-foreground/30"}`} data-testid={`plan-item-${idx}`}>
                    <div className="flex flex-col opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                      <button onClick={() => moveItem(idx, -1)} disabled={idx === 0} data-testid={`move-up-${idx}`}
                        className="text-muted-foreground hover:text-foreground disabled:opacity-20 h-4"><ChevronUp className="h-4 w-4" /></button>
                      <button onClick={() => moveItem(idx, 1)} disabled={idx === items.length - 1} data-testid={`move-down-${idx}`}
                        className="text-muted-foreground hover:text-foreground disabled:opacity-20 h-4"><ChevronDown className="h-4 w-4" /></button>
                    </div>
                    <div className={`h-11 w-11 rounded-xl flex items-center justify-center shrink-0 border ${it.done ? "border-border bg-transparent" : "border-border bg-white/[0.04]"}`}>
                      <Icon className={`h-5 w-5 ${it.done ? "text-muted-foreground" : "text-foreground/80"}`} strokeWidth={1.5} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className={`font-medium ${it.done ? "line-through text-muted-foreground" : ""}`}>{it.title}</p>
                        <span className="text-[10px] tracking-[0.12em] uppercase text-muted-foreground/70 border border-border rounded-full px-2 py-0.5">{it.type}</span>
                        {it.custom && <span className="text-[10px] tracking-[0.12em] uppercase text-foreground/60 border border-border rounded-full px-2 py-0.5">Yours</span>}
                      </div>
                      {it.detail && <p className="text-sm text-muted-foreground mt-0.5">{it.detail}</p>}
                      <p className="text-[11px] text-muted-foreground/70 font-mono-data mt-1.5">{it.duration_min} min · {it.time_of_day}</p>
                    </div>
                    <button onClick={() => delItem(idx)} data-testid={`delete-item-${idx}`}
                      className="text-muted-foreground hover:text-escalation opacity-0 group-hover:opacity-100 transition-opacity shrink-0"><Trash2 className="h-4 w-4" /></button>
                    <button onClick={() => toggleItem(idx)} data-testid={`toggle-item-${idx}`}
                      className={`h-8 w-8 rounded-full border flex items-center justify-center shrink-0 transition-all ${it.done ? "bg-primary border-primary scale-100" : "border-border hover:border-foreground hover:scale-105"}`}>
                      {it.done && <Check className="h-4 w-4 text-primary-foreground" strokeWidth={2.5} />}
                    </button>
                  </motion.div>
                );
              })}
            </div>
            {/* Add your own to-do */}
            <div className="flex gap-2 mt-4">
              <Input className="rounded-full h-11" placeholder="Add your own to-do…" value={newTodo}
                onChange={(e) => setNewTodo(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addTodo()} data-testid="todo-input" />
              <Button size="icon" className="rounded-full bg-primary text-primary-foreground hover:bg-zinc-200 shrink-0" onClick={addTodo} data-testid="add-todo-button">
                <Plus className="h-4 w-4" />
              </Button>
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

            <div className="flex flex-col sm:flex-row gap-2 mb-6">
              <div className="flex gap-1 rounded-full border border-border p-1 shrink-0">
                {MEALS.map((mm) => (
                  <button key={mm} onClick={() => setMeal(mm)} data-testid={`meal-${mm}`}
                    className={`rounded-full px-3 py-1.5 text-xs capitalize transition-colors ${meal === mm ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}>
                    {mm}
                  </button>
                ))}
              </div>
              <div className="flex gap-2 flex-1">
                <Input className="rounded-full h-11 flex-1" placeholder='Describe a meal — "2 rotis and dal"…' value={foodText}
                  onChange={(e) => setFoodText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && logFood()} data-testid="food-input" />
                <Button className="rounded-full bg-primary text-primary-foreground hover:bg-zinc-200 px-6" onClick={logFood} disabled={busy} data-testid="log-food-button">
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Log"}
                </Button>
              </div>
            </div>

            <div className="space-y-5">
              {food.logs?.length === 0 && <p className="text-sm text-muted-foreground rounded-2xl border border-border bg-card/30 p-5">Nothing logged yet today.</p>}
              {MEALS.map((mm) => {
                const group = (food.logs || []).filter((l) => (l.meal || "snack") === mm);
                if (group.length === 0) return null;
                const kcal = group.reduce((s, l) => s + (l.calories || 0), 0);
                return (
                  <div key={mm} data-testid={`meal-group-${mm}`}>
                    <div className="flex items-center justify-between mb-2 px-1">
                      <p className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground capitalize">{mm}</p>
                      <span className="text-[11px] text-muted-foreground font-mono-data">{kcal} kcal</span>
                    </div>
                    <div className="space-y-2">
                      {group.map((l) => (
                        <div key={l.id} className="group flex items-center justify-between rounded-2xl border border-border bg-card/50 p-4" data-testid={`food-log-${l.id}`}>
                          <div className="flex items-center gap-3 min-w-0">
                            <div className="h-9 w-9 rounded-lg bg-white/[0.04] border border-border flex items-center justify-center shrink-0"><Utensils className="h-4 w-4 text-foreground/70" strokeWidth={1.5} /></div>
                            <div className="min-w-0"><p className="text-sm font-medium truncate">{l.summary}</p><p className="text-[11px] text-muted-foreground font-mono-data">{l.calories} kcal · P{l.protein_g} C{l.carbs_g} F{l.fat_g}</p></div>
                          </div>
                          <button onClick={() => delFood(l.id)} className="text-muted-foreground hover:text-escalation opacity-0 group-hover:opacity-100 transition-opacity shrink-0"><Trash2 className="h-4 w-4" /></button>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </TabsContent>

          {/* SCHEDULE */}
          <TabsContent value="mood" className="mt-8">
            <h2 className="font-display font-light text-2xl mb-2 flex items-center gap-2"><Smile className="h-5 w-5 text-muted-foreground" /> How are you, really?</h2>
            <p className="text-muted-foreground mb-6">One tap a day. Over time it becomes a gentle picture of how you've been.</p>

            <div className="grid grid-cols-5 gap-2 mb-4" data-testid="mood-picker">
              {MOODS.map(({ v, label, Icon }) => {
                const active = trends.today?.mood === v;
                return (
                  <button key={v} onClick={() => logMood(v)} data-testid={`mood-${v}`}
                    className={`rounded-2xl border p-4 flex flex-col items-center gap-2 transition-all ${active ? "border-foreground bg-accent" : "border-border bg-card/40 hover:border-foreground/40"}`}>
                    <Icon className={`h-6 w-6 ${v <= 2 ? "text-rose-300/80" : v === 3 ? "text-amber-300/80" : "text-emerald-300/80"}`} strokeWidth={1.5} />
                    <span className="text-xs text-muted-foreground">{label}</span>
                  </button>
                );
              })}
            </div>
            <Input className="rounded-full h-11 mb-8" placeholder="Add a note (optional) — what's behind the feeling?"
              value={moodNote} onChange={(e) => setMoodNote(e.target.value)} data-testid="mood-note-input" />

            {/* Trend graph */}
            <div className="rounded-2xl border border-border bg-card/40 p-6" data-testid="mood-trends">
              <div className="flex items-center justify-between mb-6">
                <p className="text-sm text-muted-foreground">Last 30 days</p>
                {trends.average != null && <p className="text-sm">Average <span className="font-display text-lg">{trends.average}</span><span className="text-muted-foreground">/5</span></p>}
              </div>
              {trends.series.length === 0 ? (
                <p className="text-sm text-muted-foreground py-6 text-center">No moods logged yet — tap one above to begin.</p>
              ) : (
                <div className="flex items-end gap-1 h-32">
                  {trends.series.map((r) => (
                    <div key={r.date} className="flex-1 flex flex-col justify-end group relative" title={`${r.date}: ${r.mood}/5`}>
                      <div className={`rounded-t-md transition-all ${r.mood <= 2 ? "bg-rose-300/50" : r.mood === 3 ? "bg-amber-300/50" : "bg-emerald-300/60"} group-hover:opacity-80`}
                        style={{ height: `${(r.mood / 5) * 100}%`, minHeight: "6px" }} data-testid="mood-bar" />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="breathe" className="mt-8">
            <h2 className="font-display font-light text-2xl mb-2 flex items-center gap-2"><Wind className="h-5 w-5 text-muted-foreground" /> Take a breath</h2>
            <p className="text-muted-foreground mb-2">A minute of slow breathing settles the nervous system. Follow the circle.</p>
            <BreathingPlayer />
          </TabsContent>

          <TabsContent value="gratitude" className="mt-8">
            <h2 className="font-display font-light text-2xl mb-2 flex items-center gap-2"><Heart className="h-5 w-5 text-muted-foreground" /> Gratitude jar</h2>
            <p className="text-muted-foreground mb-6">Drop in the small good things. On a hard day, they're here waiting.</p>
            <div className="flex gap-2 mb-8">
              <Input className="rounded-full h-11" placeholder="Something good, however tiny…" value={gratInput}
                onChange={(e) => setGratInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addGratitude()} data-testid="gratitude-input" />
              <Button size="icon" className="rounded-full bg-primary text-primary-foreground hover:bg-zinc-200 shrink-0" onClick={addGratitude} data-testid="add-gratitude-button"><Plus className="h-4 w-4" /></Button>
            </div>
            {gratitude.items.length === 0 ? (
              <p className="text-sm text-muted-foreground rounded-2xl border border-border bg-card/30 p-5">Your jar is empty — add your first good moment above.</p>
            ) : (
              <div className="grid sm:grid-cols-2 gap-3" data-testid="gratitude-list">
                {gratitude.items.map((g) => (
                  <motion.div key={g.id} initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }}
                    className="group relative rounded-2xl border border-border bg-card/50 p-5" data-testid={`gratitude-${g.id}`}>
                    <Quote className="h-4 w-4 text-muted-foreground/50 mb-2" />
                    <p className="text-sm leading-relaxed">{g.text}</p>
                    <button onClick={() => delGratitude(g.id)} className="absolute top-3 right-3 text-muted-foreground hover:text-escalation opacity-0 group-hover:opacity-100 transition-opacity"><Trash2 className="h-3.5 w-3.5" /></button>
                  </motion.div>
                ))}
              </div>
            )}
          </TabsContent>

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
