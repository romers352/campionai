import React, { useState } from "react";
import PageShell from "@/components/PageShell";
import { Plus, Minus } from "lucide-react";

const FAQS = [
  { q: "Is CampionAI a therapist?", a: "No. CampionAI is an AI companion, clearly labeled as AI. It offers everyday companionship — it does not diagnose, treat, or replace professional care. When a moment turns serious, it surfaces real humans and crisis resources." },
  { q: "Is it really private?", a: "Yes. Your conversations are yours and are never used to train third-party models. You can turn on Private Mode to keep a session off the record, export everything you've shared, or delete your account and data entirely at any time." },
  { q: "How does memory work?", a: "With your consent, CampionAI remembers what matters — your context, people, goals, and preferences — so conversations feel continuous. You can view, edit, or forget any memory from the memory drawer whenever you like." },
  { q: "What happens in a crisis?", a: "If a high-risk moment is detected, CampionAI responds with calm and care, surfaces local crisis hotlines, can connect you to a verified professional, and — with your safety consent — alert a trusted contact. It is not a substitute for emergency services." },
  { q: "Who can use it?", a: "CampionAI is for adults 18 and over. You'll confirm your age during onboarding." },
  { q: "Is it free?", a: "The core companion is free for individuals. CampionAI Plus is an optional paid wellness experience (daily plans, food logging, coaching) with a free trial." },
  { q: "Does it check in on me?", a: "If you'd like. CampionAI can send thoughtful, well-timed check-ins that feel like a friend reaching out — not a notification. You control the frequency, including turning them off." },
  { q: "What languages does it support?", a: "The current MVP is English-first, on the web. More languages and platforms are on the roadmap." },
];

function Item({ q, a, index }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-t border-border" data-testid={`faq-item-${index}`}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between gap-6 py-6 text-left group"
        data-testid={`faq-toggle-${index}`}
      >
        <span className="font-display text-xl md:text-2xl font-normal text-foreground group-hover:text-foreground transition-colors">{q}</span>
        <span className="shrink-0 text-muted-foreground">{open ? <Minus className="h-5 w-5" /> : <Plus className="h-5 w-5" />}</span>
      </button>
      {open && (
        <p className="text-[15px] leading-relaxed text-muted-foreground max-w-2xl pb-7 -mt-1" data-testid={`faq-answer-${index}`}>{a}</p>
      )}
    </div>
  );
}

export default function FAQ() {
  return (
    <PageShell
      testId="faq-page"
      eyebrow="Answers"
      title="Frequently asked"
      subtitle="The things people ask most before they start talking. Still curious? Reach out any time."
    >
      <div className="border-b border-border">
        {FAQS.map((f, i) => <Item key={f.q} index={i} {...f} />)}
      </div>
    </PageShell>
  );
}
