import React from "react";
import PageShell, { Section } from "@/components/PageShell";
import { LifeBuoy, Phone, MessageSquare, Globe, ShieldAlert } from "lucide-react";

const HOTLINES = [
  { region: "United States", name: "988 Suicide & Crisis Lifeline", contact: "Call or text 988", href: "tel:988" },
  { region: "United States", name: "Crisis Text Line", contact: "Text HOME to 741741", href: "sms:741741" },
  { region: "United Kingdom & ROI", name: "Samaritans", contact: "Call 116 123", href: "tel:116123" },
  { region: "Canada", name: "Talk Suicide Canada", contact: "Call 1-833-456-4566", href: "tel:18334564566" },
  { region: "Australia", name: "Lifeline", contact: "Call 13 11 14", href: "tel:131114" },
  { region: "Europe", name: "European Emergency Number", contact: "Call 112", href: "tel:112" },
];

export default function Safety() {
  return (
    <PageShell
      testId="safety-page"
      eyebrow="You are not alone"
      title="Safety & crisis resources"
      subtitle="CampionAI is a companion, not a crisis service. If you or someone you know is struggling, real help is available right now."
    >
      {/* Emergency band — Signal Red reserved for safety */}
      <div className="border border-destructive/40 bg-destructive/[0.06] backdrop-blur-md p-6 md:p-8 rounded-2xl flex items-start gap-4" data-testid="safety-emergency-band">
        <ShieldAlert className="h-6 w-6 text-destructive shrink-0 mt-0.5" strokeWidth={1.6} />
        <div>
          <p className="font-display text-xl text-foreground mb-1">In immediate danger?</p>
          <p className="text-sm text-muted-foreground leading-relaxed">
            If you or someone else is in immediate danger, call your local emergency number now
            — <a href="tel:112" className="text-destructive font-medium underline underline-offset-4">112</a> (Europe),
            {" "}<a href="tel:911" className="text-destructive font-medium underline underline-offset-4">911</a> (US/Canada), or your country's equivalent.
          </p>
        </div>
      </div>

      <Section title="Crisis hotlines">
        <p className="mb-2">Free, confidential support is available 24/7 in most regions. You deserve to be heard.</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4 not-prose">
          {HOTLINES.map((h, i) => (
            <a
              key={i}
              href={h.href}
              className="border border-border hover:border-destructive/50 rounded-2xl p-6 transition-colors group"
              data-testid={`safety-hotline-${i}`}
            >
              <p className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground mb-3">{h.region}</p>
              <p className="font-display text-lg text-foreground mb-1 flex items-center gap-2">
                {h.contact.toLowerCase().startsWith("text") ? <MessageSquare className="h-4 w-4 text-destructive" /> : <Phone className="h-4 w-4 text-destructive" />}
                {h.name}
              </p>
              <p className="text-sm text-destructive/90 group-hover:text-destructive transition-colors">{h.contact}</p>
            </a>
          ))}
        </div>
      </Section>

      <Section title="Find a line in your country">
        <p>
          Not listed above? These directories maintain up-to-date crisis lines worldwide:
        </p>
        <p className="not-prose flex flex-col gap-3 mt-3">
          <a href="https://findahelpline.com" target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-foreground underline underline-offset-4 hover:no-underline"><Globe className="h-4 w-4" /> findahelpline.com</a>
          <a href="https://www.iasp.info/resources/Crisis_Centres/" target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-foreground underline underline-offset-4 hover:no-underline"><Globe className="h-4 w-4" /> IASP Crisis Centre directory</a>
        </p>
      </Section>

      <Section title="How CampionAI helps">
        <p className="flex items-start gap-3"><LifeBuoy className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" /> When a high-risk moment is detected, CampionAI stays calm and present, surfaces local crisis hotlines, can connect you to a verified professional, and — with your consent — can alert a trusted contact.</p>
        <p>It will never replace emergency services or professional care. Reaching out to a real person is always the bravest, kindest thing you can do.</p>
      </Section>
    </PageShell>
  );
}
