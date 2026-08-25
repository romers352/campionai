import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "@/components/ui/sonner";
import { ShieldCheck, HeartHandshake, Loader2, ArrowRight, ArrowLeft } from "lucide-react";

export default function Onboarding() {
  const { user, refresh, loading } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [countries, setCountries] = useState([]);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    preferred_name: "",
    age_confirmed: false,
    communication_style: "warm",
    country: "",
    tc_name: "",
    tc_relationship: "",
    tc_phone: "",
    tc_email: "",
    checkin_frequency: "daily",
    safety_consent: false,
  });

  useEffect(() => {
    if (!loading && !user) navigate("/auth");
    if (user?.onboarded) navigate("/chat");
    if (user?.profile?.preferred_name) setForm((f) => ({ ...f, preferred_name: user.profile.preferred_name }));
  }, [user, loading, navigate]);

  useEffect(() => {
    api.get("/meta/countries").then(({ data }) => setCountries(data));
    api.get("/meta/detect-country").then(({ data }) => {
      if (data.country) setForm((f) => ({ ...f, country: data.country }));
    }).catch(() => {});
  }, []);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const steps = [
    {
      title: "Let's get to know each other",
      valid: () => form.preferred_name.trim() && form.age_confirmed,
      body: (
        <div className="space-y-6">
          <div>
            <Label className="text-sm">What should I call you?</Label>
            <Input data-testid="onb-name-input" className="mt-1.5 rounded-full h-11" placeholder="Your preferred name"
              value={form.preferred_name} onChange={(e) => set("preferred_name", e.target.value)} />
          </div>
          <div>
            <Label className="text-sm mb-2 block">How do you like to be talked to?</Label>
            <div className="grid grid-cols-3 gap-2">
              {["warm", "playful", "direct"].map((s) => (
                <button key={s} type="button" data-testid={`onb-style-${s}`}
                  onClick={() => set("communication_style", s)}
                  className={`rounded-2xl border py-3 text-sm capitalize transition-colors ${form.communication_style === s ? "border-primary bg-primary/10 text-primary" : "border-border hover:bg-accent"}`}>
                  {s}
                </button>
              ))}
            </div>
          </div>
          <label className="flex items-start gap-3 rounded-2xl bg-accent/50 p-4 cursor-pointer">
            <Checkbox data-testid="onb-age-checkbox" checked={form.age_confirmed} onCheckedChange={(v) => set("age_confirmed", !!v)} className="mt-0.5" />
            <span className="text-sm text-muted-foreground">I confirm I am <b className="text-foreground">18 years or older</b>. CampionAI is an adults-only companion in this version.</span>
          </label>
        </div>
      ),
    },
    {
      title: "Where are you based?",
      valid: () => !!form.country,
      body: (
        <div className="space-y-6">
          <p className="text-sm text-muted-foreground">This lets me show you the right local crisis resources if you ever need them.</p>
          <div>
            <Label className="text-sm">Country</Label>
            <Select value={form.country} onValueChange={(v) => set("country", v)}>
              <SelectTrigger data-testid="onb-country-select" className="mt-1.5 rounded-full h-11">
                <SelectValue placeholder="Select your country" />
              </SelectTrigger>
              <SelectContent>
                {countries.map((c) => (
                  <SelectItem key={c.code} value={c.code}>{c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-sm mb-2 block">How often should I check in on you?</Label>
            <div className="grid grid-cols-3 gap-2">
              {[["daily", "Daily"], ["few_times_week", "A few / week"], ["off", "Only me"]].map(([v, l]) => (
                <button key={v} type="button" data-testid={`onb-freq-${v}`}
                  onClick={() => set("checkin_frequency", v)}
                  className={`rounded-2xl border py-3 text-sm transition-colors ${form.checkin_frequency === v ? "border-primary bg-primary/10 text-primary" : "border-border hover:bg-accent"}`}>
                  {l}
                </button>
              ))}
            </div>
          </div>
        </div>
      ),
    },
    {
      title: "One trusted contact",
      valid: () => form.tc_name.trim() && form.tc_relationship.trim() && (form.tc_phone.trim() || form.tc_email.trim()),
      body: (
        <div className="space-y-5">
          <p className="text-sm text-muted-foreground">
            If serious danger is ever detected, this is the one person I'll reach out to. Choose someone you trust.
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-sm">Their name</Label>
              <Input data-testid="onb-tc-name" className="mt-1.5 rounded-full h-11" value={form.tc_name} onChange={(e) => set("tc_name", e.target.value)} />
            </div>
            <div>
              <Label className="text-sm">Relationship</Label>
              <Input data-testid="onb-tc-relationship" className="mt-1.5 rounded-full h-11" placeholder="e.g. sister" value={form.tc_relationship} onChange={(e) => set("tc_relationship", e.target.value)} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-sm">Phone</Label>
              <Input data-testid="onb-tc-phone" className="mt-1.5 rounded-full h-11" value={form.tc_phone} onChange={(e) => set("tc_phone", e.target.value)} />
            </div>
            <div>
              <Label className="text-sm">Email</Label>
              <Input data-testid="onb-tc-email" type="email" className="mt-1.5 rounded-full h-11" value={form.tc_email} onChange={(e) => set("tc_email", e.target.value)} />
            </div>
          </div>
        </div>
      ),
    },
    {
      title: "Your consent & safety",
      valid: () => form.safety_consent,
      body: (
        <div className="space-y-5">
          <div className="rounded-2xl border border-escalation/30 bg-escalation/5 p-5">
            <div className="flex items-center gap-2 mb-3 text-escalation">
              <ShieldCheck className="h-5 w-5" />
              <span className="font-semibold">How my safety net works</span>
            </div>
            <ul className="text-sm text-muted-foreground space-y-2 leading-relaxed">
              <li>• I'm a companion, <b className="text-foreground">not a therapist</b>. I won't diagnose you.</li>
              <li>• If I detect serious danger, I'll automatically alert your trusted contact, surface verified professionals, and show local crisis hotlines.</li>
              <li>• You can talk to a real human anytime by asking.</li>
            </ul>
          </div>
          <label className="flex items-start gap-3 rounded-2xl bg-accent/50 p-4 cursor-pointer">
            <Checkbox data-testid="onb-consent-checkbox" checked={form.safety_consent} onCheckedChange={(v) => set("safety_consent", !!v)} className="mt-0.5" />
            <span className="text-sm text-muted-foreground">
              I understand and consent: <b className="text-foreground">if serious danger is detected, CampionAI will alert my trusted contact and connect me to a verified professional and crisis hotline.</b>
            </span>
          </label>
        </div>
      ),
    },
  ];

  const current = steps[step];

  const next = async () => {
    if (!current.valid()) { toast.error("Please complete this step to continue"); return; }
    if (step < steps.length - 1) { setStep(step + 1); return; }
    setSaving(true);
    try {
      await api.post("/onboarding", {
        preferred_name: form.preferred_name,
        age_confirmed: form.age_confirmed,
        country: form.country,
        trusted_contact: { name: form.tc_name, relationship: form.tc_relationship, phone: form.tc_phone, email: form.tc_email },
        safety_consent: form.safety_consent,
        checkin_frequency: form.checkin_frequency,
        communication_style: form.communication_style,
      });
      await refresh();
      toast.success("You're all set");
      navigate("/chat");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not complete setup");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6">
      <div className="w-full max-w-lg">
        <div className="flex items-center gap-2.5 mb-8">
          <div className="h-8 w-8 rounded-xl bg-primary flex items-center justify-center">
            <HeartHandshake className="h-4 w-4 text-primary-foreground" />
          </div>
          <span className="font-display font-extrabold text-lg">CampionAI</span>
        </div>

        <div className="flex gap-2 mb-8">
          {steps.map((_, i) => (
            <div key={i} className={`h-1.5 flex-1 rounded-full transition-colors ${i <= step ? "bg-primary" : "bg-border"}`} />
          ))}
        </div>

        <AnimatePresence mode="wait">
          <motion.div key={step}
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}>
            <h1 className="text-2xl sm:text-3xl font-extrabold font-display tracking-tight mb-6">{current.title}</h1>
            {current.body}
          </motion.div>
        </AnimatePresence>

        <div className="flex items-center justify-between mt-10">
          {step > 0 ? (
            <Button variant="ghost" className="rounded-full" onClick={() => setStep(step - 1)} data-testid="onb-back-button">
              <ArrowLeft className="h-4 w-4 mr-1" /> Back
            </Button>
          ) : <span />}
          <Button className="rounded-full px-7 h-11" onClick={next} disabled={saving} data-testid="onb-next-button">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : step === steps.length - 1 ? "Finish setup" : "Continue"}
            {!saving && step < steps.length - 1 && <ArrowRight className="h-4 w-4 ml-1.5" />}
          </Button>
        </div>
      </div>
    </div>
  );
}
