import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { ShieldCheck, Sparkles, Lock, Brain, ArrowUpRight } from "lucide-react";

const HERO_IMG =
  "https://images.unsplash.com/photo-1709625862266-014ef072fd93?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzNTl8MHwxfHNlYXJjaHwyfHxkYXJrJTIwYWJzdHJhY3QlMjBnbGFzcyUyMHJlZmxlY3Rpb258ZW58MHx8fHwxNzg3NjMxOTMwfDA&ixlib=rb-4.1.0&q=85";

const Feature = ({ icon: Icon, title, body, index }) => (
  <motion.div
    initial={{ opacity: 0, y: 16 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true }}
    transition={{ duration: 0.6, delay: index * 0.08, ease: [0.16, 1, 0.3, 1] }}
    className="border-t border-border pt-6"
    data-testid={`feature-${title.toLowerCase().replace(/\s/g, "-")}`}
  >
    <Icon className="h-5 w-5 text-muted-foreground mb-8" strokeWidth={1.5} />
    <h3 className="text-2xl font-display font-medium mb-3">{title}</h3>
    <p className="text-sm text-muted-foreground leading-relaxed max-w-xs">{body}</p>
  </motion.div>
);

export default function Landing() {
  return (
    <div className="min-h-screen bg-background text-foreground relative">
      <nav className="sticky top-0 z-30 glass">
        <div className="max-w-7xl mx-auto px-6 md:px-10 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3" data-testid="brand-logo">
            <span className="font-display font-semibold text-2xl tracking-tight">Campion<span className="italic font-light">AI</span></span>
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
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
            className="max-w-4xl"
          >
            <div className="flex items-center gap-3 mb-10 text-[10px] tracking-[0.25em] uppercase text-muted-foreground" data-testid="ai-label-badge">
              <span className="border border-border px-2.5 py-1">AI Companion</span>
              <span className="border border-border px-2.5 py-1">Adults 18+</span>
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
      </section>

      {/* Features — asymmetric */}
      <section className="max-w-7xl mx-auto px-6 md:px-10 py-24">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-10 lg:gap-12">
          <Feature index={0} icon={Brain} title="Memory, with consent" body="It holds onto what matters and forgets what you ask. View, edit, or erase anything, anytime." />
          <Feature index={1} icon={ShieldCheck} title="A real safety net" body="If serious danger is detected, it alerts your trusted contact and surfaces verified humans and crisis lines." />
          <Feature index={2} icon={Lock} title="Private by design" body="Private Mode keeps a session off the record. Your conversations are never used as training data." />
          <Feature index={3} icon={Sparkles} title="It reaches out first" body="Thoughtful, well-timed check-ins that feel like a friend — never a notification." />
        </div>
      </section>

      {/* Conversation preview */}
      <section className="max-w-7xl mx-auto px-6 md:px-10 pb-24">
        <div className="border border-border bg-white/[0.02] backdrop-blur-md p-10 md:p-16 max-w-3xl">
          <p className="text-[10px] tracking-[0.25em] uppercase text-muted-foreground mb-8">A quiet conversation</p>
          <p className="font-ai text-2xl md:text-3xl font-light leading-relaxed mb-8">
            Congrats on the new job — first-day nerves are so real. When do you start, and is coffee new for you?
          </p>
          <div className="border-l border-border pl-5 ml-auto max-w-md text-right">
            <p className="text-base text-muted-foreground">honestly I'm terrified I'll mess up the orders</p>
          </div>
        </div>
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
        <p className="text-xs text-muted-foreground mt-16 max-w-lg leading-relaxed">
          CampionAI is an AI companion — clearly labeled as AI — not a therapist or crisis service.
          If you are in immediate danger, call your local emergency number.
        </p>
      </section>
    </div>
  );
}
