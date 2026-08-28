import React, { useState } from "react";
import PageShell, { Section } from "@/components/PageShell";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/sonner";
import { Mail, Loader2, CheckCircle2, MessageSquare, ShieldQuestion } from "lucide-react";

export default function Contact() {
  const [form, setForm] = useState({ name: "", email: "", subject: "", message: "" });
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.email.trim() || !form.message.trim()) {
      toast.error("Please fill in your name, email, and message.");
      return;
    }
    setBusy(true);
    try {
      const { data } = await api.post("/contact", form);
      setSent(true);
      toast.success(data?.message || "Thanks for reaching out — we'll get back to you soon.");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const field = "w-full bg-transparent border-b border-border focus:border-foreground focus:outline-none py-3 text-foreground placeholder:text-muted-foreground/60 transition-colors";

  return (
    <PageShell
      testId="contact-page"
      eyebrow="Say hello"
      title="Get in touch"
      subtitle="Questions, feedback, press, or partnership ideas — we read everything and reply as soon as we can."
    >
      <div className="grid grid-cols-1 md:grid-cols-12 gap-12">
        {/* Info */}
        <div className="md:col-span-5 space-y-8">
          <div>
            <Mail className="h-5 w-5 text-muted-foreground mb-3" strokeWidth={1.5} />
            <p className="font-display text-xl text-foreground mb-1">Email us</p>
            <a href="mailto:hello@campionai.com" className="text-sm text-muted-foreground hover:text-foreground underline underline-offset-4">hello@campionai.com</a>
          </div>
          <div>
            <ShieldQuestion className="h-5 w-5 text-muted-foreground mb-3" strokeWidth={1.5} />
            <p className="font-display text-xl text-foreground mb-1">In crisis?</p>
            <p className="text-sm text-muted-foreground leading-relaxed">This form isn't monitored for emergencies. Please see our <a href="/safety" className="text-foreground underline underline-offset-4">safety &amp; crisis resources</a>.</p>
          </div>
          <div>
            <MessageSquare className="h-5 w-5 text-muted-foreground mb-3" strokeWidth={1.5} />
            <p className="font-display text-xl text-foreground mb-1">Product questions?</p>
            <p className="text-sm text-muted-foreground leading-relaxed">Check the <a href="/faq" className="text-foreground underline underline-offset-4">FAQ</a> — your answer may already be there.</p>
          </div>
        </div>

        {/* Form */}
        <div className="md:col-span-7">
          {sent ? (
            <div className="border border-border rounded-2xl p-10 text-center bg-white/[0.02]" data-testid="contact-success">
              <CheckCircle2 className="h-12 w-12 text-primary mx-auto mb-6" strokeWidth={1.2} />
              <h2 className="font-display font-light text-3xl tracking-tight mb-2">Message sent.</h2>
              <p className="text-muted-foreground">Thank you for reaching out — we'll be in touch soon.</p>
            </div>
          ) : (
            <form onSubmit={submit} className="space-y-7" data-testid="contact-form">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-7">
                <div>
                  <label className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground">Name</label>
                  <input className={field} value={form.name} onChange={set("name")} placeholder="Your name" data-testid="contact-name" />
                </div>
                <div>
                  <label className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground">Email</label>
                  <input type="email" className={field} value={form.email} onChange={set("email")} placeholder="you@example.com" data-testid="contact-email" />
                </div>
              </div>
              <div>
                <label className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground">Subject</label>
                <input className={field} value={form.subject} onChange={set("subject")} placeholder="What's this about? (optional)" data-testid="contact-subject" />
              </div>
              <div>
                <label className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground">Message</label>
                <textarea rows={5} className={`${field} resize-none`} value={form.message} onChange={set("message")} placeholder="Tell us more…" data-testid="contact-message" />
              </div>
              <Button type="submit" size="lg" disabled={busy} className="rounded-full px-8 bg-primary text-primary-foreground hover:bg-zinc-200" data-testid="contact-submit">
                {busy ? <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Sending…</> : "Send message"}
              </Button>
            </form>
          )}
        </div>
      </div>
    </PageShell>
  );
}
