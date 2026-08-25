import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "@/components/ui/sonner";
import AccountMenu from "@/components/AccountMenu";
import { Loader2, Upload, ShieldCheck, Clock, XCircle, CheckCircle2 } from "lucide-react";

const STATUS_UI = {
  pending: { icon: Clock, title: "Under review", tone: "text-foreground",
    body: "We're checking your licence. This usually takes a day or two — we'll email you." },
  verified: { icon: CheckCircle2, title: "You're verified", tone: "text-foreground",
    body: "Your profile is live. Head to your dashboard to go online and take sessions." },
  rejected: { icon: XCircle, title: "Not approved", tone: "text-escalation",
    body: "We couldn't approve this application." },
  suspended: { icon: XCircle, title: "Account suspended", tone: "text-escalation",
    body: "Your account is suspended. Contact support if you think this is a mistake." },
};

export default function DoctorApply() {
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [profile, setProfile] = useState(undefined); // undefined = loading, null = none
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(null);
  const [form, setForm] = useState({
    name: "", credentials: "", licence_number: "", specialty: "",
    languages: "en", country: "", bio: "", is_volunteer: false, session_price: "",
    licence_doc_path: null, photo_path: null,
  });

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const load = async () => {
    try {
      const { data } = await api.get("/doctor/me");
      setProfile(data);
    } catch {
      setProfile(null);
    }
  };
  useEffect(() => { load(); }, []);

  const upload = async (field, file) => {
    if (!file) return;
    setUploading(field);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post("/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
      set(field, data.path);
      toast.success("Uploaded");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Upload failed");
    } finally { setUploading(null); }
  };

  const submit = async () => {
    const required = ["name", "credentials", "licence_number", "country"];
    for (const k of required) {
      if (!String(form[k] || "").trim()) return toast.error(`${k.replace("_", " ")} is required`);
    }
    if (form.country.trim().length !== 2) return toast.error("Use a 2-letter country code, e.g. NP or US");
    if (!form.is_volunteer && !(parseFloat(form.session_price) > 0)) {
      return toast.error("Set a session price, or tick the volunteer box");
    }
    if (!form.licence_doc_path) return toast.error("Upload your licence document");

    setBusy(true);
    try {
      await api.post("/doctor/apply", {
        ...form,
        country: form.country.trim().toUpperCase(),
        languages: form.languages.split(",").map((s) => s.trim()).filter(Boolean),
        session_price: form.is_volunteer ? 0 : parseFloat(form.session_price),
      });
      await refresh();
      await load();
      toast.success("Application submitted");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Couldn't submit");
    } finally { setBusy(false); }
  };

  const startKyc = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/doctor/kyc/start");
      window.open(data.url, "_blank", "noopener");
      toast.success("Verification opened in a new tab");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Couldn't start verification");
      await load();
    } finally { setBusy(false); }
  };

  const refreshKyc = async () => {
    try {
      const { data } = await api.get("/doctor/kyc/refresh");
      toast.success(`Identity check: ${data.status}`);
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Nothing to check");
    }
  };

  if (profile === undefined) {
    return <div className="min-h-screen bg-background flex items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  }

  const Header = () => (
    <header className="glass sticky top-0 z-20 h-16 flex items-center justify-between px-6">
      <span className="font-display font-semibold text-xl tracking-tight">Join as a doctor</span>
      <AccountMenu />
    </header>
  );

  // ---- Already applied: show status + the identity step ----
  if (profile) {
    const ui = STATUS_UI[profile.status] || STATUS_UI.pending;
    const kycStatus = profile.kyc?.status || "not_started";
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="max-w-xl mx-auto px-6 py-14">
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
            <div className="border border-border bg-card/40 rounded-2xl p-8 mb-6" data-testid="doctor-status-card">
              <ui.icon className={`h-8 w-8 mb-5 ${ui.tone}`} strokeWidth={1.2} />
              <h1 className="font-display font-light text-3xl tracking-tight mb-3" data-testid="doctor-status">{ui.title}</h1>
              <p className="text-muted-foreground leading-relaxed">{ui.body}</p>
              {profile.review_reason && (
                <p className="text-sm text-muted-foreground mt-4 border-l-2 border-border pl-4">{profile.review_reason}</p>
              )}
              {profile.status === "verified" && (
                <Button className="rounded-full mt-7 bg-primary text-primary-foreground hover:bg-zinc-200"
                  onClick={() => navigate("/doctor")} data-testid="go-dashboard">Open dashboard</Button>
              )}
            </div>

            {profile.status !== "verified" && (
              <div className="border border-border bg-card/40 rounded-2xl p-8" data-testid="kyc-card">
                <ShieldCheck className="h-6 w-6 text-foreground/70 mb-4" strokeWidth={1.5} />
                <p className="font-medium mb-1">Identity verification</p>
                <p className="text-sm text-muted-foreground mb-2">
                  Confirms you're the person on your ID. Your licence is reviewed separately by our team.
                </p>
                <p className="text-sm mb-6">
                  Status: <span className="font-mono-data" data-testid="kyc-status">{kycStatus}</span>
                </p>
                <div className="flex gap-2 flex-wrap">
                  {kycStatus !== "approved" && (
                    <Button className="rounded-full bg-primary text-primary-foreground hover:bg-zinc-200"
                      onClick={startKyc} disabled={busy} data-testid="start-kyc">
                      {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : kycStatus === "pending" ? "Continue verification" : "Verify my identity"}
                    </Button>
                  )}
                  {profile.kyc?.session_id && (
                    <Button variant="outline" className="rounded-full border-border" onClick={refreshKyc} data-testid="refresh-kyc">
                      Check status
                    </Button>
                  )}
                </div>
              </div>
            )}
          </motion.div>
        </div>
      </div>
    );
  }

  // ---- Application form ----
  const FileRow = ({ field, label, hint }) => (
    <div>
      <Label className="text-sm">{label}</Label>
      <div className="mt-1.5 flex items-center gap-3">
        <label className="flex-1 flex items-center gap-3 rounded-full border border-border px-4 h-10 cursor-pointer hover:bg-accent transition-colors">
          {uploading === field ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4 text-muted-foreground" />}
          <span className="text-sm truncate text-muted-foreground">
            {form[field] ? form[field].split("/").pop() : hint}
          </span>
          <input type="file" className="hidden" accept="image/*,application/pdf"
            onChange={(e) => upload(field, e.target.files?.[0])} data-testid={`upload-${field}`} />
        </label>
        {form[field] && <CheckCircle2 className="h-4 w-4 text-foreground/70 shrink-0" />}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="max-w-xl mx-auto px-6 py-14">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display font-light text-4xl tracking-tight mb-3">Offer your time.</h1>
          <p className="text-muted-foreground mb-10 leading-relaxed">
            People reach CampionAI at hard moments. Some need a real clinician. Set your own rate,
            or volunteer — volunteers are the only doctors free users can reach.
          </p>

          <div className="space-y-4" data-testid="doctor-apply-form">
            {[["name", "Full name", "Dr Jane Adhikari"],
              ["credentials", "Credentials", "MBBS, MD Psychiatry"],
              ["licence_number", "Licence number", "NMC-12345"],
              ["specialty", "Specialty", "Anxiety, crisis support"],
              ["languages", "Languages (comma separated)", "en, ne"],
              ["country", "Country code", "NP"]].map(([k, l, ph]) => (
              <div key={k}>
                <Label className="text-sm">{l}</Label>
                <Input className="mt-1.5 rounded-full h-10" placeholder={ph} value={form[k]}
                  onChange={(e) => set(k, e.target.value)} data-testid={`apply-${k}`} />
              </div>
            ))}

            <div>
              <Label className="text-sm">Short bio</Label>
              <Textarea className="mt-1.5 rounded-2xl" rows={3} placeholder="A few sentences people will read before booking."
                value={form.bio} onChange={(e) => set("bio", e.target.value)} data-testid="apply-bio" />
            </div>

            <FileRow field="licence_doc_path" label="Licence document" hint="Upload a photo or PDF" />
            <FileRow field="photo_path" label="Profile photo (optional)" hint="A friendly headshot" />

            <label className="flex items-start gap-3 cursor-pointer rounded-2xl border border-border p-4">
              <Checkbox checked={form.is_volunteer} onCheckedChange={(v) => set("is_volunteer", !!v)} data-testid="apply-volunteer" />
              <span>
                <span className="text-sm font-medium block">I want to volunteer</span>
                <span className="text-sm text-muted-foreground">Free sessions, reachable by people who can't pay.</span>
              </span>
            </label>

            {!form.is_volunteer && (
              <div>
                <Label className="text-sm">Your rate per session (USD)</Label>
                <Input type="number" min="1" step="1" className="mt-1.5 rounded-full h-10" placeholder="40"
                  value={form.session_price} onChange={(e) => set("session_price", e.target.value)} data-testid="apply-price" />
                <p className="text-xs text-muted-foreground mt-2">A platform commission is deducted; you're paid out separately.</p>
              </div>
            )}

            <Button className="w-full rounded-full mt-4 bg-primary text-primary-foreground hover:bg-zinc-200"
              onClick={submit} disabled={busy} data-testid="apply-submit">
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Submit application"}
            </Button>
            <p className="text-xs text-muted-foreground text-center">
              You'll verify your identity next. Your licence is reviewed by a person.
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
