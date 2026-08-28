import React from "react";
import PageShell, { Section } from "@/components/PageShell";

export default function Privacy() {
  return (
    <PageShell
      testId="privacy-page"
      eyebrow="Legal"
      title="Privacy Policy"
      subtitle="Privacy is not a feature here — it's the foundation. This explains what we collect, why, and the control you always keep."
    >
      <p className="text-xs text-muted-foreground mb-10">Last updated: {new Date().getFullYear()}</p>

      <Section title="Our promise">
        <p>CampionAI is built privacy-first. Your conversations are yours. We do not sell your data, and we never use your private conversations to train third-party models.</p>
      </Section>

      <Section title="What we collect">
        <p>• <span className="text-foreground">Account details</span> — your email and a securely hashed password.</p>
        <p>• <span className="text-foreground">Profile & context</span> — the name, preferences, and details you choose to share during onboarding and chat.</p>
        <p>• <span className="text-foreground">Memories</span> — only what the memory engine saves with your consent. You can view, edit, or erase any memory at any time.</p>
        <p>• <span className="text-foreground">Safety events</span> — if a high-risk moment is detected, we log the event so we can connect you with help.</p>
      </Section>

      <Section title="Private Mode">
        <p>Turn on Private Mode and that session stays off the record — nothing from it is stored as long-term memory. It's your quiet space, whenever you need it.</p>
      </Section>

      <Section title="How we use your data">
        <p>To provide the companion experience, remember what matters (with permission), keep you safe, and improve the product. We never advertise to you and never sell your information.</p>
      </Section>

      <Section title="Your controls">
        <p>• <span className="text-foreground">Export</span> everything you've shared as a JSON download.</p>
        <p>• <span className="text-foreground">Delete everything</span> — a one-tap, permanent wipe of your account and data.</p>
        <p>• <span className="text-foreground">Forget</span> individual memories from the memory drawer.</p>
      </Section>

      <Section title="Data sharing">
        <p>We share data only when you ask us to (e.g. a human handoff summary you approve, or alerting a trusted contact during a safety escalation) or when required by law.</p>
      </Section>

      <Section title="Contact">
        <p>Questions about your privacy? Reach us any time through the <a href="/contact" className="text-foreground underline underline-offset-4 hover:no-underline">contact page</a>.</p>
      </Section>
    </PageShell>
  );
}
