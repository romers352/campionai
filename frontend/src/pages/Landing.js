import React, { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import Footer from "@/components/Footer";
import {
  ShieldCheck, Sparkles, Lock, Brain, ArrowUpRight, MessageSquareText,
  HeartHandshake, LifeBuoy, Check,
} from "lucide-react";

const HERO_IMG =
  "https://images.unsplash.com/photo-1709625862266-014ef072fd93?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzNTl8MHwxfHNlYXJjaHwyfHxkYXJrJTIwYWJzdHJhY3QlMjBnbGFzcyUyMHJlZmxlY3Rpb258ZW58MHx8fHwxNzg3NjMxOTMwfDA&ixlib=rb-4.1.0&q=85";
const PLUS_IMG =
  "https://images.unsplash.com/photo-1650804068570-7fb2e3dbf888?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzNTl8MHwxfHNlYXJjaHwxfHxvYnNpZGlhbiUyMHRleHR1cmV8ZW58MHx8fGJsYWNrfDE3ODc4ODY2ODZ8MA&ixlib=rb-4.1.0&q=85";

const fade = (delay = 0) => ({
  initial: { opacity: 0, y: 18 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-80px" },
  transition: { duration: 0.7, delay, ease: [0.16, 1, 0.3, 1] },
});

const Feature = ({ icon: Icon, title, body, index }) => (
  <motion.div {...fade(index * 0.08)} className="border-t border-border pt-6" data-testid={`feature-${title.toLowerCase().replace(/\s/g, "-")}`}>
    <Icon className="h-5 w-5 text-muted-foreground mb-8" strokeWidth={1.5} />
    <h3 className="text-2xl font-display font-medium mb-3">{title}</h3>
    <p className="text-sm text-muted-foreground leading-relaxed max-w-xs">{body}</p>
  </motion.div>
);

const Step = ({ n, title, body, icon: Icon, index }) => (
  <motion.div {...fade(index * 0.1)} className="relative" data-testid={`how-step-${n}`}>
    <div className="flex items-center gap-4 mb-6">
      <span className="font-mono-data text-xs text-muted-foreground border border-border rounded-full h-9 w-9 flex items-center justify-center">{n}</span>
      <Icon className="h-5 w-5 text-muted-foreground" strokeWidth={1.5} />
    </div>
    <h3 className="font-display text-2xl font-medium mb-3">{title}</h3>
    <p className="text-sm text-muted-foreground leading-relaxed max-w-sm">{body}</p>
  </motion.div>
);

export default function Landing() {
  const location = useLocation();

  // Support in-page anchors like /#how from the footer.
  useEffect(() => {
    if (location.hash) {
      const el = document.querySelector(location.hash);
      if (el) setTimeout(() => el.scrollIntoView({ behavior: "smooth" }), 60);
    }
  }, [location.hash]);

  return (
    <div className="min-h-screen bg-background text-foreground relative">
      <nav className="sticky top-0 z-30 glass">
        <div className="max-w-7xl mx-auto px-6 md:px-10 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3" data-testid="brand-logo">
            <span className="font-display font-semibold text-2xl tracking-tight">Campion<span className="italic font-light">AI</span></span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm text-muted-foreground">
            <a href="#how" className="hover:text-foreground transition-colors">How it works</a>
            <a href="#plus" className="hover:text-foreground transition-colors">Plus</a>
            <Link to="/safety" className="hover:text-foreground transition-colors">Safety</Link>
            <Link to="/faq" className="hover:text-foreground transition-colors">FAQ</Link>
          </div>
          <div className="flex items-center gap-2">
            <Link to="/auth" data-testid="nav-signin-link">
              <Button variant="ghost" className="rounded-full text-muted-foreground hover:text-foreground">Sign in</Button>
            </Link>
            <Link to="/auth" data-testid="nav-getstarted-link">
              <Button className="rounded-full px-6 bg-primary text-primary-foreground hover:bg-zinc-200">Get started</Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 z-0">
          <img src={HERO_IMG} alt="" className="w-full h-full object-cover opacity-40" />
          <div className="absolute inset-0 bg-gradient-to-b from-background/60 via-background/80 to-background" />
        </div>

        <div className="relative z-10 max-w-7xl mx-auto px-6 md:px-10 pt-28 pb-32 md:pt-40 md:pb-48">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }} className="max-w-4xl">
            <div className="flex items-center gap-3 mb-10 text-[10px] tracking-[0.25em] uppercase text-muted-foreground" data-testid="ai-label-badge">
              <span className="border border-border px-2.5 py-1">AI Companion</span>
              <span className="border border-border px-2.5 py-1">Adults 18+</span>
              <span className="border border-border px-2.5 py-1">Privacy-first</span>
            </div>
            <h1 className="font-display font-light text-5xl sm:text-7xl lg:text-[5.5rem] leading-[0.95] tracking-tight mb-8">
              A companion that
              <br />
              <span className="italic font-normal">actually remembers you.</span>
            </h1>
            <p className="text-lg text-muted-foreground max-w-lg leading-relaxed mb-12">
              A warm, private presence for late nights and ordinary days. It knows your context, reaches
              out on its own, and — when things get heavy — connects you to real people who can help.
            </p>
            <div className="flex flex-wrap items-center gap-6">
              <Link to="/auth" data-testid="hero-getstarted-link">
                <Button size="lg" className="rounded-full px-8 h-13 py-3.5 text-base bg-primary text-primary-foreground hover:bg-zinc-200 group">
                  Start talking
                  <ArrowUpRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                </Button>
              </Link>
              <span className="text-sm text-muted-foreground">Free for individuals</span>
            </div>
          </motion.div>
        </div>

        {/* Trust row */}
        <div className="relative z-10 max-w-7xl mx-auto px-6 md:px-10 pb-6">
          <motion.div {...fade(0.1)} className="grid grid-cols-2 md:grid-cols-4 border-t border-border">
            {[
              { k: "Private by design", v: "Your words stay yours" },
              { k: "Remembers you", v: "With consent, always" },
              { k: "Reaches out first", v: "Thoughtful check-ins" },
              { k: "Real safety net", v: "Humans when it counts" },
            ].map((s, i) => (
              <div key={i} className={`py-8 md:py-10 ${i !== 0 ? "md:border-l border-border md:pl-8" : ""}`} data-testid={`trust-${i}`}>
                <p className="font-display text-lg text-foreground mb-1">{s.k}</p>
                <p className="text-xs text-muted-foreground tracking-wide">{s.v}</p>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Features — asymmetric */}
      <section className="max-w-7xl mx-auto px-6 md:px-10 py-24">
        <motion.p {...fade()} className="text-[10px] tracking-[0.3em] uppercase text-muted-foreground mb-12">What makes it different</motion.p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-10 lg:gap-12">
          <Feature index={0} icon={Brain} title="Memory, with consent" body="It holds onto what matters and forgets what you ask. View, edit, or erase anything, anytime." />
          <Feature index={1} icon={ShieldCheck} title="A real safety net" body="If serious danger is detected, it alerts your trusted contact and surfaces verified humans and crisis lines." />
          <Feature index={2} icon={Lock} title="Private by design" body="Private Mode keeps a session off the record. Your conversations are never used as training data." />
          <Feature index={3} icon={Sparkles} title="It reaches out first" body="Thoughtful, well-timed check-ins that feel like a friend — never a notification." />
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="max-w-7xl mx-auto px-6 md:px-10 py-24 scroll-mt-24">
        <div className="border-t border-border pt-16">
          <motion.h2 {...fade()} className="font-display font-light text-4xl md:text-6xl tracking-tight mb-4 max-w-2xl">
            Getting started takes <span className="italic">a minute.</span>
          </motion.h2>
          <motion.p {...fade(0.05)} className="text-muted-foreground max-w-lg mb-16">Three small steps to a companion that grows with you.</motion.p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-14 md:gap-10">
            <Step index={0} n="01" icon={MessageSquareText} title="Say hello" body="Create your account and tell it your name. No lengthy forms — just a warm start." />
            <Step index={1} n="02" icon={HeartHandshake} title="Share your world" body="A gentle 4-step onboarding: your context, a trusted contact, and how often you'd like check-ins." />
            <Step index={2} n="03" icon={Brain} title="Talk, and it remembers" body="Chat any time. With your consent it remembers what matters, so every conversation feels continuous." />
          </div>
        </div>
      </section>

      {/* Conversation preview */}
      <section className="max-w-7xl mx-auto px-6 md:px-10 pb-24">
        <motion.div {...fade()} className="border border-border bg-white/[0.02] backdrop-blur-md p-10 md:p-16 max-w-3xl">
          <p className="text-[10px] tracking-[0.25em] uppercase text-muted-foreground mb-8">A quiet conversation</p>
          <p className="font-ai text-2xl md:text-3xl font-light leading-relaxed mb-8">
            Congrats on the new job — first-day nerves are so real. When do you start, and is coffee new for you?
          </p>
          <div className="border-l border-border pl-5 ml-auto max-w-md text-right">
            <p className="text-base text-muted-foreground">honestly I'm terrified I'll mess up the orders</p>
          </div>
        </motion.div>
      </section>

      {/* Plus teaser */}
      <section id="plus" className="max-w-7xl mx-auto px-6 md:px-10 pb-24 scroll-mt-24">
        <motion.div {...fade()} className="relative overflow-hidden rounded-3xl border border-border">
          <div className="absolute inset-0">
            <img src={PLUS_IMG} alt="" className="w-full h-full object-cover opacity-30" />
            <div className="absolute inset-0 bg-gradient-to-r from-background via-background/90 to-background/40" />
          </div>
          <div className="relative z-10 p-10 md:p-16 max-w-2xl">
            <div className="flex items-center gap-2 mb-6 text-[10px] tracking-[0.25em] uppercase text-muted-foreground">
              <Sparkles className="h-3.5 w-3.5" /> CampionAI Plus
            </div>
            <h2 className="font-display font-light text-4xl md:text-5xl tracking-tight mb-5">
              A daily wellness partner, <span className="italic">woven in.</span>
            </h2>
            <p className="text-muted-foreground leading-relaxed mb-8 max-w-lg">
              Optional Plus adds AI-built daily plans — meditation, movement, breathing — natural-language food
              logging, a simple schedule, and gentle coaching in your chats.
            </p>
            <ul className="space-y-3 mb-10">
              {["Personalized plan, refreshed daily", "Log meals in plain language", "Coaching woven into conversation", "14-day free trial"].map((t) => (
                <li key={t} className="flex items-center gap-3 text-sm text-foreground/85">
                  <Check className="h-4 w-4 text-primary shrink-0" /> {t}
                </li>
              ))}
            </ul>
            <Link to="/auth" data-testid="plus-cta">
              <Button size="lg" className="rounded-full px-8 bg-primary text-primary-foreground hover:bg-zinc-200">Try Plus free</Button>
            </Link>
          </div>
        </motion.div>
      </section>

      {/* Safety band — Signal Red reserved for safety */}
      <section className="max-w-7xl mx-auto px-6 md:px-10 pb-24">
        <motion.div {...fade()} className="border border-destructive/30 bg-destructive/[0.05] rounded-3xl p-10 md:p-14 flex flex-col md:flex-row md:items-center gap-8 justify-between" data-testid="landing-safety-band">
          <div className="flex items-start gap-5 max-w-2xl">
            <LifeBuoy className="h-7 w-7 text-destructive shrink-0 mt-1" strokeWidth={1.5} />
            <div>
              <h2 className="font-display text-2xl md:text-3xl font-normal text-foreground mb-2">When it matters, real people step in.</h2>
              <p className="text-sm text-muted-foreground leading-relaxed">
                CampionAI is a companion, not a crisis service. If serious risk is detected, it surfaces crisis
                hotlines, connects verified professionals, and can alert your trusted contact.
              </p>
            </div>
          </div>
          <Link to="/safety" data-testid="landing-safety-link">
            <Button variant="outline" className="rounded-full border-destructive/40 text-destructive hover:bg-destructive/10 hover:text-destructive">Safety resources</Button>
          </Link>
        </motion.div>
      </section>

      {/* CTA */}
      <section className="max-w-7xl mx-auto px-6 md:px-10 pb-32">
        <div className="border-t border-border pt-20 flex flex-col md:flex-row md:items-end justify-between gap-10">
          <h2 className="font-display font-light text-4xl md:text-6xl tracking-tight max-w-xl">
            Someone in your corner, <span className="italic">every day.</span>
          </h2>
          <Link to="/auth" data-testid="cta-getstarted-link">
            <Button size="lg" className="rounded-full px-8 h-13 py-3.5 text-base bg-primary text-primary-foreground hover:bg-zinc-200">
              Create your companion
            </Button>
          </Link>
        </div>
      </section>

      <Footer />
    </div>
  );
}
