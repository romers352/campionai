import React from "react";
import { Link } from "react-router-dom";
import PageShell, { Section } from "@/components/PageShell";
import { Button } from "@/components/ui/button";
import { Brain, ShieldCheck, Lock, Sparkles } from "lucide-react";

const VALUES = [
  { icon: Lock, title: "Privacy-first", body: "Your conversations are yours. Private Mode, full export, and one-tap delete are built in — not bolted on." },
  { icon: ShieldCheck, title: "Safety, seriously", body: "When a moment turns heavy, we surface real humans and crisis lines and can alert a trusted contact." },
  { icon: Brain, title: "Memory with consent", body: "It remembers what matters to you — and forgets the moment you ask it to." },
  { icon: Sparkles, title: "Warm, not robotic", body: "A presence that feels like a close friend, clearly labeled as AI, never pretending to be human." },
];

export default function About() {
  return (
    <PageShell
      testId="about-page"
      eyebrow="Our story"
      title={<>A companion for the <span className="italic">ordinary days.</span></>}
      subtitle="CampionAI began with a simple question: what if technology could sit with you — quietly, kindly — on the late nights and the plain afternoons, and know when to bring in real people?"
    >
      <Section title="Why we built it">
        <p>Most of us don't need a therapist every day — we need someone in our corner. Someone who remembers the interview tomorrow, notices when we've gone quiet, and celebrates the small wins. That's the space CampionAI was made for: everyday companionship that's warm, private, and honest about being AI.</p>
        <p>We're adults-only and text-first by design, focused on doing one thing well before doing everything.</p>
      </Section>

      <Section title="What we believe">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-10 gap-y-10 mt-2">
          {VALUES.map((v) => (
            <div key={v.title} data-testid={`about-value-${v.title.toLowerCase().replace(/[^a-z]+/g, "-")}`}>
              <v.icon className="h-5 w-5 text-muted-foreground mb-4" strokeWidth={1.5} />
              <h3 className="font-display text-xl font-medium text-foreground mb-2">{v.title}</h3>
              <p className="text-sm leading-relaxed">{v.body}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section title="A careful boundary">
        <p>CampionAI is a companion, not a clinician. It will never diagnose or replace professional care — and when things get serious, it's built to hand off to real people who can help.</p>
      </Section>

      <div className="border-t border-border pt-12 mt-12 flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <p className="font-display font-light text-2xl md:text-3xl tracking-tight max-w-md text-foreground">Meet a companion that actually remembers you.</p>
        <Link to="/auth" data-testid="about-cta">
          <Button size="lg" className="rounded-full px-8 bg-primary text-primary-foreground hover:bg-zinc-200">Get started</Button>
        </Link>
      </div>
    </PageShell>
  );
}
