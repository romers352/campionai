import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { ShieldCheck, Sparkles, Lock, HeartHandshake, ArrowRight, Brain } from "lucide-react";

const Feature = ({ icon: Icon, title, body }) => (
  <motion.div
    initial={{ opacity: 0, y: 12 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true }}
    transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
    className="rounded-3xl bg-card p-8 ambient-shadow border border-border/60"
    data-testid={`feature-${title.toLowerCase().replace(/\s/g, "-")}`}
  >
    <div className="h-11 w-11 rounded-2xl bg-primary/12 flex items-center justify-center mb-5">
      <Icon className="h-5 w-5 text-primary" />
    </div>
    <h3 className="text-lg font-semibold mb-2 font-display">{title}</h3>
    <p className="text-sm text-muted-foreground leading-relaxed">{body}</p>
  </motion.div>
);

export default function Landing() {
  return (
    <div className="min-h-screen bg-background text-foreground relative">
      <nav className="sticky top-0 z-30 glass">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5" data-testid="brand-logo">
            <div className="h-8 w-8 rounded-xl bg-primary flex items-center justify-center">
              <HeartHandshake className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="font-display font-extrabold text-lg tracking-tight">CampionAI</span>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/auth" data-testid="nav-signin-link">
              <Button variant="ghost" className="rounded-full">Sign in</Button>
            </Link>
            <Link to="/auth" data-testid="nav-getstarted-link">
              <Button className="rounded-full px-5">Get started</Button>
            </Link>
          </div>
        </div>
      </nav>

      <section className="max-w-6xl mx-auto px-6 pt-20 pb-16 md:pt-28 relative">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
          className="max-w-3xl"
        >
          <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 text-primary px-4 py-1.5 text-xs font-medium mb-7" data-testid="ai-label-badge">
            <Sparkles className="h-3.5 w-3.5" /> An AI companion — always clearly labeled as AI
          </div>
          <h1 className="text-4xl sm:text-6xl font-extrabold font-display tracking-tight leading-[1.05] mb-6">
            A companion that
            <br />
            <span className="text-primary">actually remembers you.</span>
          </h1>
          <p className="text-lg text-muted-foreground max-w-xl leading-relaxed mb-9">
            CampionAI is a warm, private daily companion. It knows your context, checks in on its own,
            and — when things get serious — connects you to real people who can help.
          </p>
          <div className="flex flex-wrap items-center gap-4">
            <Link to="/auth" data-testid="hero-getstarted-link">
              <Button size="lg" className="rounded-full px-7 h-12 text-base group">
                Start talking
                <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </Button>
            </Link>
            <span className="text-sm text-muted-foreground">Free for individuals · Adults 18+</span>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="mt-16 rounded-[2rem] border border-border/60 bg-card p-6 md:p-8 ambient-shadow-lg max-w-2xl"
        >
          <div className="flex items-start gap-3 mb-5">
            <div className="h-8 w-8 rounded-full bg-primary/15 flex items-center justify-center shrink-0 mt-0.5">
              <HeartHandshake className="h-4 w-4 text-primary" />
            </div>
            <p className="text-[15px] leading-relaxed">
              Hey — congrats on the new job! First-day nerves are so real. When do you start, and is coffee new for you?
            </p>
          </div>
          <div className="flex justify-end">
            <div className="rounded-3xl rounded-br-md bg-secondary px-5 py-3 text-[15px] max-w-[80%]">
              honestly I'm terrified I'll mess up the orders 😅
            </div>
          </div>
        </motion.div>
      </section>

      <section className="max-w-6xl mx-auto px-6 py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          <Feature icon={Brain} title="Memory that respects you" body="It remembers what matters — and forgets what you ask. View, edit, or delete anything, anytime." />
          <Feature icon={ShieldCheck} title="A real safety net" body="If serious danger is detected, it alerts your trusted contact and surfaces verified humans and crisis lines." />
          <Feature icon={Lock} title="Private by design" body="Private Mode keeps sessions off the record. Your conversations are never used as training data." />
          <Feature icon={Sparkles} title="Checks in on you" body="Thoughtful, well-timed check-ins that feel like a friend reaching out — never spammy." />
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 pb-24">
        <div className="rounded-[2rem] bg-primary text-primary-foreground p-10 md:p-14 relative overflow-hidden">
          <div className="relative z-10 max-w-xl">
            <h2 className="text-3xl md:text-4xl font-extrabold font-display tracking-tight mb-4">
              Someone in your corner, every day.
            </h2>
            <p className="text-primary-foreground/85 mb-8 leading-relaxed">
              Set up your companion in under two minutes. Add one trusted contact, and you're ready.
            </p>
            <Link to="/auth" data-testid="cta-getstarted-link">
              <Button size="lg" variant="secondary" className="rounded-full px-7 h-12 text-base">
                Create your companion
              </Button>
            </Link>
          </div>
        </div>
        <p className="text-center text-xs text-muted-foreground mt-8 max-w-lg mx-auto leading-relaxed">
          CampionAI is an AI companion, not a therapist or crisis service. If you are in immediate danger,
          call your local emergency number.
        </p>
      </section>
    </div>
  );
}
