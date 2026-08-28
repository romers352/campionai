import React from "react";
import PageShell, { Section } from "@/components/PageShell";

export default function Terms() {
  return (
    <PageShell
      testId="terms-page"
      eyebrow="Legal"
      title="Terms of Service"
      subtitle="The plain-language agreement for using CampionAI. By creating an account you agree to these terms."
    >
      <p className="text-xs text-muted-foreground mb-10">Last updated: {new Date().getFullYear()}</p>

      <Section title="Who can use CampionAI">
        <p>CampionAI is for adults 18 and over. You confirm your age during onboarding. If you are under 18, please do not use the service.</p>
      </Section>

      <Section title="What CampionAI is — and isn't">
        <p>CampionAI is an AI companion, clearly labeled as AI. It is <span className="text-foreground">not</span> a therapist, doctor, or crisis service, and it does not diagnose or provide medical advice. In an emergency, contact your local emergency number or a crisis line.</p>
      </Section>

      <Section title="Your account">
        <p>Keep your login credentials secure. You're responsible for activity on your account. Let us know right away if you suspect unauthorized access.</p>
      </Section>

      <Section title="Acceptable use">
        <p>Please don't use CampionAI to harm others, break the law, or attempt to disrupt or reverse-engineer the service. We may suspend accounts that do.</p>
      </Section>

      <Section title="CampionAI Plus & payments">
        <p>Plus is an optional paid wellness experience with a free trial. Subscriptions renew per the plan you choose until cancelled. Donations are voluntary and non-refundable. Pricing and features may change with notice.</p>
      </Section>

      <Section title="Content & memory">
        <p>You own what you share. You grant us the limited permission needed to operate the service (store memories with consent, provide context to the companion). You can delete your data at any time.</p>
      </Section>

      <Section title="Disclaimers">
        <p>The service is provided “as is.” We work hard to keep it reliable and safe, but we can't guarantee it will be uninterrupted or error-free, and it is not a substitute for professional care.</p>
      </Section>

      <Section title="Changes">
        <p>We may update these terms as the product evolves. We'll post the new date above and, for material changes, give you a heads-up in-app.</p>
      </Section>
    </PageShell>
  );
}
